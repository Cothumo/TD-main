// Sphere - the Sepulcra sphere, appearing now and then in TDA (between ink_layer and nin_stage).
// A black sphere with a liquid circumference grows out of the picture, stays a while and collapses again. It bends
// everything around it (gravitational lensing + a slow swirl drawn into it), its edge undulates like a liquid surface
// and surges on hits, a corona breathes with the music (light in the dark picture, a shadow halo on white paper), and on
// strong hits plasma bursts from its limb (Penumbra). The Ambient Ink is pulled to it as solar plasma meanwhile.
// input 0 = the picture (ink_layer/OUT).
uniform vec4 uP;   // presence (0..1), centre x, y (0..1), radius (fraction of the frame width, at full presence)
uniform vec4 uH;   // time (s), level (smoothed), hit envelope, seconds since the hit
uniform vec4 uQ;   // Lens, Liquid, Corona, Bursts
uniform vec4 uR;   // Swirl, Rim, burst angle (rad), 0
out vec4 fragColor;
#define PI 3.14159265
float h21(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y);
}
float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 4; i++) { s += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; } return s / 0.9375; }
float anf(float a, float k, vec2 s) { return fbm(vec2(cos(a), sin(a)) * k + s); }       // seamless around the circle
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
vec3 tex(vec2 uv) { return texture(sTD2DInputs[0], clamp(uv, vec2(0.001), vec2(0.999))).rgb; }

void main() {
	vec2 uv = vUV.st;
	vec2 R2 = uTDOutputInfo.res.zw;
	float asp = R2.x / R2.y;                         // width / height
	float pres = clamp(uP.x, 0.0, 1.0);
	vec3 base = tex(uv);
	if (pres < 0.001) { fragColor = TDOutputSwizzle(vec4(base, 1.0)); return; }
	float t = uH.x, lvl = uH.y, hit = uH.z, hage = uH.w;
	float lens = uQ.x, liquid = uQ.y, corona = uQ.z, bursts = uQ.w;
	vec2 c = uP.yz;
	float R = uP.w * smoothstep(0.0, 1.0, pres);    // grows out of a point and collapses back into it

	// width units: x as is, y scaled so the sphere is round
	vec2 q = vec2(uv.x - c.x, (uv.y - c.y) / asp);
	float d = length(q) + 1e-5, a = atan(q.y, q.x);
	// the liquid circumference: the edge undulates like the surface of a drop, surging with the music and on hits
	// smooth, slow swells (no crags): two low harmonics travelling round the edge, plus soft ripples on hits
	float wob = (anf(a, 1.3, vec2(t * 0.30, 1.0)) - 0.5) + 0.35 * (anf(a, 2.4, vec2(-t * 0.55, 4.0)) - 0.5)
	          + 0.25 * hit * sin(a * 7.0 - hage * 9.0) * exp(-hage * 1.5);
	float Rl = R * (1.0 + liquid * wob * (0.07 + 0.06 * lvl + 0.10 * hit));

	// gravity: everything around is bent towards the sphere (lensing) and slowly drawn round it (swirl)
	float k = lens * pres * R * R * 1.4;
	float bend = k / (d * d + 0.25 * R * R);
	float sw = uR.x * pres * 0.9 * R / (d + 0.5 * R) * (0.5 + 0.5 * lvl);
	float cs = cos(sw), sn = sin(sw);
	vec2 qr = vec2(cs * q.x - sn * q.y, sn * q.x + cs * q.y) * max(0.0, 1.0 - bend);
	vec2 suv = c + vec2(qr.x, qr.y * asp);
	vec3 col = tex(suv);
	float paper = smoothstep(0.35, 0.75, (luma(tex(vec2(0.2, 0.25))) + luma(tex(vec2(0.8, 0.75))) + luma(tex(vec2(0.5, 0.1)))) / 3.0);

	// the corona: light that breathes with the music around the edge (a shadow halo on white paper)
	float ed = max(d - Rl, 0.0);
	float cor = exp(-ed / (R * (0.18 + 0.25 * lvl))) * corona * (0.35 + 0.5 * lvl + 0.4 * hit);
	cor *= 0.75 + 0.25 * anf(a, 3.0, vec2(t * 0.2, 7.0));
	// plasma bursts from the limb on strong hits: radial filaments shooting out and falling back
	float pb = 0.0;
	if (bursts > 0.0 && hit > 0.01) {
		float sector = exp(-pow(atan(sin(a - uR.z), cos(a - uR.z)) / 0.9, 2.0)) + 0.5 * exp(-pow(atan(sin(a - uR.z - 2.4), cos(a - uR.z - 2.4)) / 0.6, 2.0));
		float fil = fbm(vec2(a * 9.0, ed / R * 3.0 - hage * 2.5));
		float reach = R * (0.3 + 2.2 * (1.0 - exp(-hage * 2.0)));
		pb = smoothstep(0.5, 0.85, fil) * sector * exp(-ed / reach) * smoothstep(0.0, 0.02, ed) * hit * bursts;
	}
	float glow = clamp(cor + pb * 1.4, 0.0, 1.5) * pres;
	col = mix(col + vec3(0.85) * glow, col * (1.0 - 0.6 * clamp(glow, 0.0, 1.0)), paper);

	// the body: black, with a faint liquid sheen (the lensed scene reflected in it) and a thin bright rim on its edge
	float body = 1.0 - smoothstep(Rl - 0.004, Rl + 0.002, d);
	vec3 refl = tex(c - vec2(q.x, q.y * asp) * 0.6) * 0.07 * (1.0 - d / max(Rl, 1e-4));
	vec3 inner = vec3(0.012) + refl;
	float rim = exp(-abs(d - Rl) / 0.0025) * uR.y * (0.5 + 0.6 * lvl + 0.6 * hit);
	col = mix(col, inner, body * pres);
	col += vec3(0.9) * rim * pres * (1.0 - 0.6 * paper);

	fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
