/* Claim codes -- mirror of src/claimcode.py; keep the two in sync.
 *
 * HMAC-SHA256(secret, shipId), first 40 bits, Crockford base32 as
 * XXXX-XXXX.  The alphabet has no I, L, O or U so a plotted code can be
 * read back off card stock; normalise() folds the look-alikes a person
 * might type anyway.
 */
export const ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
export const CODE_CHARS = 8;
const GROUP = 4;
const DIGEST_BYTES = (CODE_CHARS * 5) / 8; // 40 bits
const LOOKALIKES = { I: "1", L: "1", O: "0" };

async function hmacSha256(secret, message) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  return new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(message)));
}

/** "XXXX-XXXX" for shipId under secret. */
export async function claimCode(shipId, secret) {
  if (!shipId) throw new Error("ship id is empty");
  if (!secret) throw new Error("claim secret is empty");
  const digest = await hmacSha256(secret, shipId);
  let value = 0n;
  for (let i = 0; i < DIGEST_BYTES; i++) value = (value << 8n) | BigInt(digest[i]);
  const chars = [];
  for (let i = 0; i < CODE_CHARS; i++) {
    const shift = BigInt(5 * (CODE_CHARS - 1 - i));
    chars.push(ALPHABET[Number((value >> shift) & 31n)]);
  }
  const groups = [];
  for (let i = 0; i < CODE_CHARS; i += GROUP) groups.push(chars.slice(i, i + GROUP).join(""));
  return groups.join("-");
}

/** Typed text -> bare 8 characters, or null when it cannot be a code. */
export function normalise(text) {
  if (typeof text !== "string") return null;
  let bare = text.toUpperCase().replace(/[^\p{L}\p{N}]/gu, "");
  bare = bare.replace(/[ILO]/g, (ch) => LOOKALIKES[ch]);
  if (bare.length !== CODE_CHARS) return null;
  for (const ch of bare) if (!ALPHABET.includes(ch)) return null;
  return bare;
}

/** Constant-time equality of two strings via fixed-size digests. */
export async function timingSafeEqualStrings(a, b) {
  const enc = new TextEncoder();
  const [ha, hb] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(String(a))),
    crypto.subtle.digest("SHA-256", enc.encode(String(b))),
  ]);
  if (typeof crypto.subtle.timingSafeEqual === "function") {
    return crypto.subtle.timingSafeEqual(ha, hb);
  }
  // Node (tests) has no subtle.timingSafeEqual: XOR-accumulate over the
  // fixed 32-byte digests, which never short-circuits.
  const x = new Uint8Array(ha), y = new Uint8Array(hb);
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= x[i] ^ y[i];
  return diff === 0;
}

/** True when `typed` is the code for shipId. */
export async function verifyCode(shipId, typed, secret) {
  const bare = normalise(typed);
  if (bare === null) return false;
  const expected = (await claimCode(shipId, secret)).replace(/-/g, "");
  return timingSafeEqualStrings(bare, expected);
}
