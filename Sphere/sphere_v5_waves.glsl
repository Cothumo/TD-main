// Sphere - a small, half-concealed black hole drifting through TDA now and then. You notice it more by what it does
// to the space around it - the scene bending, swirling and rippling round it - than by itself. It is the LAST layer (after nin_stage), so the NIN
// distortions never touch it, while its own gravity bends everything behind it.
//   - event horizon: a soft, vague darkness that swells and shrinks while it drifts (no rim, no rings)
//   - gravity, most of all close to it: the space sags towards it and twists round it, the scene is torn into radial
//     streaks falling into it (spaghettification), it seethes with turbulence, slow gravitational waves run out on hits;
//     the Ambient Ink is pulled in as plasma
//   - on strong hits faint jets shoot out along its axis and fade
//   - Sepulcra / Penumbra: soft organic waves radiate out of it - wobbling, breaking up, refracting the scene, faint light
//     on their crests; fine corona filaments at its edge flicker with the hi-hats; heat shimmer round it on unstable
//     sound; a dim, dusty shaft of light passes through it. All local to the hole, no flashes.
// Grey only: light in the dark picture, shadow on white paper. input 0 = the picture (nin_stage/OUT).
uniform vec4 uP;   // presence (0..1), centre x, y (0..1), horizon radius (fraction of the frame width)
uniform vec4 uH;   // time (s), level (smoothed), hit envelope, seconds since the hit
uniform vec4 uQ;   // Lens (gravity strength), Streaks (spaghettification), -, Jets
uniform vec4 uR;   // Swirl (twist), -, jet axis angle (rad), -
uniform vec4 uS;   // -, -, Reach (how far its gravity reaches, in horizon radii), Conceal (0 = a clear black disc, 1 = barely there)
uniform vec4 uW;   // Waves (radiating waves), Wavespeed, Corona (filaments at the edge), Shimmer (heat shimmer)
uniform vec4 uX;   // Shaft (dim shaft of light through it), hat, onset, flicker (smoothed, from nin_stage/echo)
out vec4 fragColor;
#define PI 3.14159265
float h21(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y);
}
float h21p(vec2 i, float per) { i.x = mod(i.x, per); return h21(i); }
float vnP(vec2 p, float per) {   // value noise periodic in x (for angles: no seam)
	vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21p(i, per), h21p(i + vec2(1, 0), per), f.x), mix(h21p(i + vec2(0, 1), per), h21p(i + vec2(1, 1), per), f.x), f.y);
}
float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; } return s / 0.96875; }
float anf(float a, float k, vec2 s) { return fbm(vec2(cos(a), sin(a)) * k + s); }
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
	float hat = clamp(uX.y, 0.0, 1.0), ons = clamp(uX.z, 0.0, 1.0), flk = clamp(uX.w, 0.0, 1.0);
	// ---- radiating waves (Sepulcra): soft fronts running out of the hole; their radius wobbles, they break into
	//      drifting segments, refract the scene they pass and carry a faint light on their crests
	float WR = 0.0;
	if (uW.x > 0.0) {
		float lam = R * 1.1;
		float dw = d + R * 0.55 * (anf(a, 1.6, vec2(t * 0.11, 2.0)) - 0.5) + R * 0.35 * (fbm(q / R * 0.7 + vec2(0.0, t * 0.08)) - 0.5);
		float ph = dw / lam - t * 0.32 * uW.y;
		float s = sin(ph * 2.0 * PI);
		float brk = smoothstep(0.36, 0.64, anf(a, 2.3, vec2(dw / (R * 3.2) - t * 0.05 * uW.y, 5.0)));
		float wenv = smoothstep(R * 1.05, R * 1.9, d) * (1.0 - smoothstep(Rg * 0.9, Rg * 2.3, d)) * pow(R / d, 0.6);
		float wamp = uW.x * pres * wenv * brk * (0.35 + 0.45 * lvl + 0.6 * ons);
		vec2 nr = qr / max(length(qr), 1e-5);
		qr += nr * cos(ph * 2.0 * PI) * R * 0.09 * wamp;                  // refraction
		WR = pow(max(s, 0.0), 3.0) * wamp;                                // crest light
	}
	// ---- heat shimmer round it: a fine, rising wobble that grows on unstable sound
	if (uW.w > 0.0) {
		float senv = smoothstep(R * 0.7, R * 1.15, d) * (1.0 - smoothstep(R * 1.6, Rg * 1.3, d));
		vec2 hp = q / R * 5.0 + vec2(0.0, -t * 1.1);
		vec2 sh = vec2(vnoise(hp + vec2(t * 0.7, 0.0)), vnoise(hp * 1.3 + vec2(9.1, 4.2))) - 0.5;
		qr += sh * R * 0.07 * uW.w * (0.12 + 0.88 * flk) * senv * pres;
	}
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
	// faint jets along its axis on strong hits (lines, not rings)
	float da = uR.z;
	float jet = 0.0;
	if (uQ.w > 0.0 && hit > 0.01) {
		vec2 ax = vec2(-sin(da), cos(da));
		float along = abs(dot(q, ax)), across = abs(dot(q, vec2(ax.y, -ax.x)));
		float len = R * (1.0 + 7.0 * (1.0 - exp(-hage * 1.8)));
		jet = exp(-across / (0.004 + 0.06 * along)) * smoothstep(R * 0.8, R * 1.4, along) * exp(-along / len)
		    * (0.6 + 0.4 * fbm(vec2(along * 40.0 - hage * 8.0, 1.0))) * hit * uQ.w * pres;
	}
	col = mix(col + vec3(0.8) * jet * 0.5, col * (1.0 - 0.45 * clamp(jet, 0.0, 1.0)), paper);
	// the horizon: a soft, vague darkness (no rim, no ring)
	float conceal = clamp(uS.w, 0.0, 1.0);
	float wob = (anf(a, 1.3, vec2(t * 0.3, 1.0)) - 0.5) + 0.25 * hit * sin(a * 5.0 - hage * 7.0) * exp(-hage * 1.5);
	float Rh = R * (1.0 + 0.08 * wob);
	col = mix(col + vec3(0.7) * WR * 0.06, col * (1.0 - 0.05 * WR), paper);
	float hole = 1.0 - smoothstep(Rh * mix(0.9, 0.35, conceal), Rh * mix(1.05, 1.35, conceal), d);
	col = mix(col, col * 0.04, hole * pres * mix(1.0, 0.82, conceal));
	// ---- corona: fine radial filaments just outside the edge, flickering softly with the hi-hats
	float cor = 0.0;
	if (uW.z > 0.0) {
		float x = (a + PI) / (2.0 * PI) * 90.0;
		float lr = log(d / max(R, 1e-5));
		float fil = vnP(vec2(x, lr * 2.5 - t * 0.2), 90.0) * vnP(vec2(x * 2.0 + 11.0, lr * 4.0 - t * 0.33), 180.0);
		fil = smoothstep(0.12, 0.62, fil);
		float fl = vnP(vec2(x * 0.5, t * 5.0), 45.0);
		float fall = smoothstep(R * 0.85, R * 1.05, d) * exp(-max(d - R, 0.0) / (R * 0.45));
		cor = fil * fall * (0.3 + 0.9 * hat * fl) * uW.z * pres;
	}
	// ---- a dim shaft of light passing through it, slowly turning, dusty
	float shf = 0.0;
	if (uX.x > 0.0) {
		float sa = da + 1.3 + 0.35 * sin(t * 0.045);
		vec2 ax = vec2(cos(sa), sin(sa));
		float al = dot(q, ax), ac = dot(q, vec2(-ax.y, ax.x));
		float wd = R * (0.4 + 0.18 * abs(al) / R);
		shf = exp(-ac * ac / (wd * wd)) * exp(-abs(al) / (Rg * 1.1)) * (0.45 + 0.55 * fbm(vec2(al / R * 1.3 - t * 0.12, ac / R * 2.5)))
		    * mix(1.0, 0.55, hole) * uX.x * pres * (0.55 + 0.45 * lvl);
	}
	float lit = cor * 0.22 + shf * 0.1;
	col = mix(col + vec3(0.85) * lit, col * (1.0 - 0.6 * lit), paper);
	fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
