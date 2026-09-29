// k6 WebSocket echo scenario: each VU opens one connection to /ws, sends MSGS messages back-to-back (waiting for
// each echo), then closes. Reports messages/s and echo round-trip latency. Run with:
//   k6 run --vus 64 --duration 15s -e URL=ws://proxy:8080/ws -e HOST=app.lab -e MSGS=200 --summary-export=/work/ws.json /k6/ws.js
import ws from 'k6/ws';
import { check } from 'k6';
import { Trend, Counter } from 'k6/metrics';

const rtt = new Trend('ws_echo_rtt_ms', true);
const msgs = new Counter('ws_messages');
const url = __ENV.URL || 'ws://proxy:8080/ws';
const host = __ENV.HOST || 'app.lab';
const N = parseInt(__ENV.MSGS || '200');
const payload = 'x'.repeat(parseInt(__ENV.SIZE || '128'));

export default function () {
  const res = ws.connect(url, { headers: { Host: host } }, function (socket) {
    let i = 0;
    let t0 = 0;
    socket.on('open', function () { t0 = Date.now(); socket.send(payload); });
    socket.on('message', function (m) {
      rtt.add(Date.now() - t0);
      msgs.add(1);
      i++;
      if (i >= N) { socket.close(); return; }
      t0 = Date.now();
      socket.send(payload);
    });
    socket.on('error', function (e) { if (e.error() !== 'websocket: close sent') { console.error('ws error: ' + e.error()); } });
    socket.setTimeout(function () { socket.close(); }, 60000);
  });
  check(res, { 'status is 101': (r) => r && r.status === 101 });
}
