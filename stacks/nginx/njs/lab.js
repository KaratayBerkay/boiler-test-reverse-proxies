// njs handler used by the pxlab nginx config: HS256 JWT verification (auth_jwt is NGINX Plus only).
import crypto from 'crypto';
import fs from 'fs';

function b64urlDecode(s) {
    return Buffer.from(s, 'base64url').toString();
}

function jwt(r) {
    const auth = r.headersIn['Authorization'] || '';
    if (!auth.startsWith('Bearer ')) {
        r.headersOut['WWW-Authenticate'] = 'Bearer realm="pxlab"';
        r.return(401, 'missing bearer token\n');
        return;
    }
    const parts = auth.slice(7).split('.');
    if (parts.length !== 3) { r.return(401, 'malformed token\n'); return; }
    let header, payload;
    try {
        header = JSON.parse(b64urlDecode(parts[0]));
        payload = JSON.parse(b64urlDecode(parts[1]));
    } catch (e) { r.return(401, 'malformed token\n'); return; }
    if (header.alg !== 'HS256') { r.return(401, 'unsupported alg\n'); return; }
    const secret = fs.readFileSync('/auth/jwt.secret');
    const expected = crypto.createHmac('sha256', secret).update(parts[0] + '.' + parts[1]).digest('base64url');
    if (expected !== parts[2]) { r.return(401, 'bad signature\n'); return; }
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp && payload.exp < now) { r.return(401, 'expired\n'); return; }
    if (payload.nbf && payload.nbf > now) { r.return(401, 'not yet valid\n'); return; }
    r.headersOut['X-JWT-Sub'] = payload.sub || '';
    r.return(200);
}

export default { jwt };
