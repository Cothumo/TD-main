// Sphere - a small, half-concealed black hole drifting through TDA now and then. You notice it more by what it does
// to the space around it - the scene bending, swirling and rippling round it - than by itself. It is the LAST layer (after nin_stage), so the NIN
// distortions never touch it, while its own gravity bends everything behind it.
//   - event horizon: a soft, vague darkness that swells and shrinks while it drifts (no rim, no rings)
//   - gravity, most of all close to it: the space sags towards it and twists round it, the scene is torn into radial
//     streaks falling into it (spaghettification), it seethes with turbulence, slow gravitational waves run out on hits;
//     the Ambient Ink is pulled in as plasma
//   - now and then its two beams flash out along its axis for a split second, spinning round fast
// Grey only: light in the dark picture, shadow on white paper. input 0 = the picture (nin_stage/OUT).
uniform vec4 uP;   // presence (0..1), centre x, y (0..1), horizon radius (fraction of the frame width)
uniform vec4 uH;   // time (s), level (smoothed), hit envelope, seconds since the hit
uniform vec4 uQ;   // Lens (gravity strength), Streaks (spaghettification), -, -
uniform vec4 uR;   // Swirl (twist), -, jet axis angle (rad), -
uniform vec4 uS;   // -, -, Reach (how far its gravity reaches, in horizon radii), Conceal (0 = a clear black disc, 1 = barely there)
uniform vec4 uF;   // -, beam flash envelope, beam axis angle (rad, spinning while it flashes), Beam (strength)
uniform vec4 uT;   // Fibers (fine filament streams swirling into it), Fiberspeed, bass swell (0..1), -
out vec4 fragColor;
#define PI 3.14159265
float h21(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y);
}
float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; } return s / 0.96875; }
float sfbm(vec2 p) { return (vnoise(p) * 0.7 + vnoise(p * 1.9 + 7.3) * 0.3); }   // smooth (2 octaves): soft liquid lobes
float anf(float a, float k, vec2 s) { return fbm(vec2(cos(a), sin(a)) * k + s); }
float h21p(vec2 i, float per) { i.x = mod(i.x, per); return h21(i); }
float vnP(vec2 p, float per) {   // value noise periodic in x (angles without a seam)
	vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21p(i, per), h21p(i + vec2(1, 0), per), f.x), mix(h21p(i + vec2(0, 1), per), h21p(i + vec2(1, 1), per), f.x), f.y);
}
// fine filament streams spiralling into the hole, like smoke pulled in: ridges of noise turned by a differential
// rotation (faster close in), so they shear into spiral filaments; two phases cross-fade so they never wind up tight
float fibers(vec2 q, float R, float t, float spd) {
	float rr = length(q) / max(R, 1e-5);
	float s = 0.0;
	for (int k = 0; k < 2; k++) {
		float fk = float(k);
		float ph = fract(t * 0.05 * spd + 0.5 * fk);
		float wgt = 1.0 - abs(2.0 * ph - 1.0);
		float th = ph * 2.4 / pow(max(rr, 0.7), 1.5) + t * 0.12 * spd / (rr + 0.4);
		float c = cos(th), sn = sin(th);
		vec2 p2 = vec2(c * q.x - sn * q.y, sn * q.x + c * q.y) / max(R, 1e-5) * 1.3 + vec2(11.0 * fk, 3.0 * fk);
		float n = fbm(p2);
		float ridge = 1.0 - abs(2.0 * fbm(p2 * 2.1 + n * 1.6 + 5.0) - 1.0);
		s += pow(ridge, 7.0) * wgt;
	}
	return s;
}
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
vec3 tex(vec2 uv) { uv = 1.0 - abs(1.0 - mod(abs(uv), 2.0)); return texture(sTD2DInputs[0], clamp(uv, vec2(0.001), vec2(0.999))).rgb; }   // mirrored at the edges (no streaks)

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

	// ---- gravity. No rings: the space sags towards it, twists round it (much more close in), is torn into radial
	//      streaks falling into it (spaghettification), seethes with turbulence near it and ripples on hits
	float Rg = R * max(uS.z, 1.0);
	float near = exp(-d / (R * 1.4));                                  // 1 at the hole, fading within a couple of radii
	float sag = uQ.x * pres * (0.12 * Rg * Rg / (d * d + Rg * Rg) + 0.55 * R * R / (d * d + 0.8 * R * R)) * (1.0 - smoothstep(Rg * 0.8, Rg * 1.8, d));
	vec2 qs = q * (1.0 - min(sag, 0.88));
	float sw = uR.x * pres * (2.4 * R / (d + 0.35 * R) + 1.0 * Rg / (d + Rg)) * (0.85 + 0.15 * sin(t * 0.25))
	         * (1.0 - smoothstep(Rg * 0.5, Rg * 1.5, d));                  // the twist stays close to it
	float cs = cos(sw), sn = sin(sw);
	vec2 qr = vec2(cs * qs.x - sn * qs.y, sn * qs.x + cs * qs.y);
	vec2 tb = vec2(fbm(q / max(R, 1e-4) * 1.2 + vec2(t * 0.4, 0.0)), fbm(q / max(R, 1e-4) * 1.2 + vec2(3.7, -t * 0.35))) - 0.5;
	qr += tb * R * 0.9 * near * uQ.x * pres;                           // turbulence close to it
	float wave = sin((d / R) * 2.0 - t * 1.2 - hage * 3.0) * exp(-d / (Rg * 0.55)) * (0.3 + 0.7 * hit) * 0.035 * uQ.x * pres;
	qr *= 1.0 + wave;
	// streaks: the scene smeared along the radius, falling into the hole (stronger close in)
	vec3 col = vec3(0.0); float ws = 0.0;
	float st = 0.10 * uQ.y * near * pres;
	for (int k = 0; k < 8; k++) {
		float f = float(k) / 7.0;
		float w = 1.0 - 0.6 * f;
		col += tex(c + vec2(qr.x, qr.y * asp) * (1.0 - st * f)) * w; ws += w;
	}
	col /= ws;
	// light near it is dimmed (it climbs out of the well) - a soft shadow larger than the hole
	col *= mix(1.0, smoothstep(R * 0.5, R * 2.6, d), 0.75 * pres * (1.0 - 0.6 * paper));
	// its two beams: only a split-second flash now and then, spinning round fast while it lasts
	float jet = 0.0;
	if (uF.w > 0.0 && uF.y > 0.001) {
		float da = uF.z;
		vec2 ax = vec2(-sin(da), cos(da));
		float along = abs(dot(q, ax)), across = abs(dot(q, vec2(ax.y, -ax.x)));
		float len = R * 5.0;
		jet = exp(-across / (0.003 + 0.05 * along)) * smoothstep(R * 0.8, R * 1.4, along) * exp(-along / len)
		    * (0.6 + 0.4 * fbm(vec2(along * 40.0 - t * 20.0, 1.0))) * uF.y * uF.w * pres;
	}
	col = mix(col + vec3(0.8) * jet * 0.6, col * (1.0 - 0.5 * clamp(jet, 0.0, 1.0)), paper);
	// the horizon: a soft, vague darkness (no rim, no ring)
	float conceal = clamp(uS.w, 0.0, 1.0);
	// fine filament streams swirling into it (Consequences): visible gravity, the hole itself stays round
	if (uT.x > 0.001) {
		float rr = d / max(R, 1e-5);
		float fz = smoothstep(0.85, 1.25, rr) * (1.0 - smoothstep(max(uS.z, 1.5) * 0.9, max(uS.z, 1.5) * 2.1, rr));
		float fb = fibers(q, R, t, uT.y) * fz * uT.x * pres * (0.7 + 0.5 * uT.z) * (1.15 / (0.6 + rr * 0.4));
		col = mix(col + vec3(0.55) * fb, col * (1.0 - 0.6 * clamp(fb, 0.0, 1.0)), paper);
	}
	float Rh = R * (1.0 + 0.02 * (anf(a, 1.3, vec2(t * 0.3, 1.0)) - 0.5));          // round - only the faintest breathing of its edge
	float hole = 1.0 - smoothstep(Rh * mix(0.9, 0.35, conceal), Rh * mix(1.05, 1.35, conceal), d);
	col = mix(col, col * 0.04, hole * pres * mix(1.0, 0.82, conceal));
	fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
