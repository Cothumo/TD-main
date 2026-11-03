// Sphere - a small, half-concealed black hole drifting through TDA now and then. You notice it more by what it does
// to the space around it - the scene bending, swirling and rippling round it - than by itself. It is the LAST layer (after nin_stage), so the NIN
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
uniform vec4 uS;   // Spin, Corona, Reach (how far its gravity reaches, in horizon radii), Conceal (0 = a clear black disc, 1 = barely there)
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

	// ---- gravity, reaching far: the scene is pulled in and magnified into a ring (lensing), dragged round the hole
	//      (frame dragging, stronger close in) and rippled by slow gravitational waves that run out of it on hits
	float Rg = R * max(uS.z, 1.0);
	// Einstein lensing: inside the Einstein radius the scene appears mirrored, outside it is stretched into a ring
	float E = uQ.x * pres * 1.5 * R;
	vec2 qs = q * (1.0 - (E * E) / (d * d + 0.02 * R * R));
	// a gentle pull reaching far out (the space sags towards it), frame dragging, and slow gravitational waves
	qs *= 1.0 - 0.32 * uQ.x * pres * Rg * Rg / (d * d + Rg * Rg);
	float sw = uR.x * pres * (1.4 * Rg / (d + Rg) * (Rg / (d + 0.6 * Rg)) + 0.2 * sin(t * 0.3));
	float wave = sin((d / R) * 2.2 - t * 1.4 - hage * 3.0) * exp(-d / (Rg * 1.5)) * (0.25 + 0.75 * hit) * 0.05 * uQ.x * pres;
	float cs = cos(sw), sn = sin(sw);
	vec2 qr = vec2(cs * qs.x - sn * qs.y, sn * qs.x + cs * qs.y) * (1.0 + wave);
	vec3 col = tex(c + vec2(qr.x, qr.y * asp));
	// light near the hole is dimmed (it climbs out of the well) - a soft shadow larger than the hole
	col *= mix(1.0, smoothstep(R * 0.6, R * 4.0, d), 0.7 * pres * (1.0 - 0.6 * paper));

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
	float conceal = clamp(uS.w, 0.0, 1.0);
	float hole = 1.0 - smoothstep(Rh * mix(0.97, 0.45, conceal), Rh * mix(1.01, 1.25, conceal), d);   // a soft, vague edge
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
	float light = (discFar + arcM * uQ.z * (1.0 - hole) + ring + cor + jet) * pres * (1.0 - 0.5 * conceal);
	col = mix(col + vec3(0.8) * light * 0.55, col * (1.0 - 0.5 * clamp(light, 0.0, 1.0)), paper);
	col = mix(col, col * 0.04, hole * pres * mix(1.0, 0.8, conceal));   // the horizon swallows the light (not quite all of it)
	float nl = discNear * pres * (1.0 - 0.5 * conceal);
	col = mix(col + vec3(0.8) * nl * 0.55, col * (1.0 - 0.5 * clamp(nl, 0.0, 1.0)), paper);
	fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
