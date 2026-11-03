// Sphere - a small black hole that appears now and then in TDA. It is the LAST layer (after nin_stage), so the NIN
// distortions never touch it, while its own gravity bends everything behind it.
//   - event horizon: a black disc with a faint liquid shiver on its edge
//   - photon ring: a hair-thin ring of light just outside it
//   - accretion disc: a thin, tilted ring of matter swirling round it (faster inside), one side a little brighter
//     (Doppler); behind the hole its far side is lensed up over the top as a thin arc, like a real black hole
//   - gravity: lensing (the scene is bent into a ring round it) and a slow swirl; the Ambient Ink is pulled in as plasma
//   - on strong hits faint jets shoot out along its axis and fade
// Grey only: light in the dark picture, shadow on white paper. input 0 = the picture (nin_stage/OUT).
uniform vec4 uP;   // presence (0..1), centre x, y (0..1), horizon radius (fraction of the frame width)
uniform vec4 uH;   // time (s), level (smoothed), hit envelope, seconds since the hit
uniform vec4 uQ;   // Lens, Liquid, Disc, Jets
uniform vec4 uR;   // Swirl, Ring, disc angle (rad), Inclination (0 = edge-on, 1 = face-on)
uniform vec4 uS;   // Spin, Corona, 0, 0
out vec4 fragColor;
#define PI 3.14159265
float h21(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y);
}
float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; } return s / 0.96875; }
float anf(float a, float k, vec2 s) { return fbm(vec2(cos(a), sin(a)) * k + s); }
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
vec3 tex(vec2 uv) { return texture(sTD2DInputs[0], clamp(uv, vec2(0.001), vec2(0.999))).rgb; }

// matter of the accretion disc at disc-plane radius r (in horizon radii) and angle a: swirling streaks
float matter(float r, float a, float t, float spin) {
	float w = a + t * spin * 1.6 / pow(max(r, 1.0), 1.5);          // inner parts orbit faster
	float n = fbm(vec2(log(r) * 7.0, w * 3.0 / PI * 2.0));
	float streak = fbm(vec2(r * 9.0, w * 5.0));
	float band = smoothstep(1.55, 1.9, r) * (1.0 - smoothstep(3.0, 4.2, r));
	return band * (0.35 + 0.65 * n) * (0.6 + 0.4 * streak) * (1.2 / r);
}

void main() {
	vec2 uv = vUV.st;
	vec2 RS = uTDOutputInfo.res.zw;
	float asp = RS.x / RS.y;
	float pres = clamp(uP.x, 0.0, 1.0);
	vec3 base = tex(uv);
	if (pres < 0.001) { fragColor = TDOutputSwizzle(vec4(base, 1.0)); return; }
	float t = uH.x, lvl = uH.y, hit = uH.z, hage = uH.w;
	vec2 c = uP.yz;
	float R = uP.w * smoothstep(0.0, 1.0, pres);
	vec2 q = vec2(uv.x - c.x, (uv.y - c.y) / asp);
	float d = length(q) + 1e-5, a = atan(q.y, q.x);
	float paper = smoothstep(0.35, 0.75, (luma(tex(vec2(0.2, 0.25))) + luma(tex(vec2(0.8, 0.75))) + luma(tex(vec2(0.5, 0.1)))) / 3.0);

	// ---- gravity: lensing (strong close in) and a slow swirl
	float k = uQ.x * pres * R * R * 2.2;
	float bend = k / (d * d + 0.1 * R * R);
	float sw = uR.x * pres * 0.7 * R / (d + 0.3 * R);
	float cs = cos(sw), sn = sin(sw);
	vec2 qr = vec2(cs * q.x - sn * q.y, sn * q.x + cs * q.y) * max(0.0, 1.0 - bend);
	vec3 col = tex(c + vec2(qr.x, qr.y * asp));
	// light near the hole is dimmed (it climbs out of the well)
	col *= mix(1.0, smoothstep(R * 0.9, R * 3.0, d), 0.6 * pres * (1.0 - paper));

	// ---- the accretion disc in its own (tilted) plane
	float da = uR.z, inc = clamp(uR.w, 0.05, 1.0);
	vec2 rq = vec2(cos(-da) * q.x - sin(-da) * q.y, sin(-da) * q.x + cos(-da) * q.y);
	vec2 dp = vec2(rq.x, rq.y / inc);                                   // the disc is a flattened ring on screen
	float dr = length(dp) / max(R, 1e-5), dang = atan(dp.y, dp.x);
	float near = step(rq.y, 0.0);                                       // the half of the disc in front of the hole
	float m = matter(dr, dang, t, uS.x) * (0.7 + 0.5 * lvl);
	m *= 1.0 + 0.45 * cos(dang);                                        // Doppler: the approaching side is brighter
	// behind the hole the far side of the disc is lensed up over the top (and under the bottom) as a thin arc
	float rr = d / max(R, 1e-5);
	float arcR = 1.55 + 0.25 * (1.0 - inc);
	float arc = exp(-pow((rr - arcR) / 0.18, 2.0)) * (0.5 + 0.5 * abs(sin(a - da)));
	float arcM = arc * matter(2.2, a - da + PI, t, uS.x) * 1.4 * (0.7 + 0.5 * lvl);
	// ---- event horizon (with a faint liquid shiver) and the photon ring
	float wob = (anf(a, 1.3, vec2(t * 0.3, 1.0)) - 0.5) + 0.25 * hit * sin(a * 7.0 - hage * 9.0) * exp(-hage * 1.5);
	float Rh = R * (1.0 + uQ.y * wob * (0.03 + 0.03 * lvl + 0.05 * hit));
	float hole = 1.0 - smoothstep(Rh - 0.0025, Rh + 0.0015, d);
	float ring = exp(-pow((d - Rh * 1.12) / (0.0035 + 0.02 * R), 2.0)) * uR.y * (0.45 + 0.4 * lvl + 0.3 * hit);
	float cor = exp(-max(d - Rh, 0.0) / (R * 0.9)) * uS.y * (0.15 + 0.25 * lvl);
	// ---- jets along the axis on strong hits
	float jet = 0.0;
	if (uQ.w > 0.0 && hit > 0.01) {
		vec2 ax = vec2(-sin(da), cos(da));
		float along = abs(dot(q, ax)), across = abs(dot(q, vec2(ax.y, -ax.x)));
		float len = R * (1.0 + 7.0 * (1.0 - exp(-hage * 1.8)));
		jet = exp(-across / (0.004 + 0.06 * along)) * smoothstep(R * 0.8, R * 1.4, along) * exp(-along / len)
		    * (0.6 + 0.4 * fbm(vec2(along * 40.0 - hage * 8.0, 1.0))) * hit * uQ.w;
	}
	float discFar = m * (1.0 - near) * (1.0 - hole) * uQ.z;            // far half: hidden by the hole
	float discNear = m * near * uQ.z;                                    // near half: passes in front of the hole
	float light = (discFar + arcM * uQ.z * (1.0 - hole) + ring + cor + jet) * pres;
	col = mix(col + vec3(0.8) * light * 0.55, col * (1.0 - 0.5 * clamp(light, 0.0, 1.0)), paper);
	col = mix(col, vec3(0.006), hole * pres);                            // the horizon swallows everything
	float nl = discNear * pres;
	col = mix(col + vec3(0.8) * nl * 0.55, col * (1.0 - 0.5 * clamp(nl, 0.0, 1.0)), paper);
	fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
