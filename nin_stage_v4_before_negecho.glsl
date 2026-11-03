// NIN Stage - the last layer of TDA, a show in three acts that the scene moves through by itself:
//   act 1 STATIC  - the picture breaks up like a failing analog signal: it dissolves into fine monochrome static in
//                   drifting bands, rows tear sideways on hits, scanlines, a slow vertical roll (Broken / Year Zero era)
//   act 2 MELT    - video feedback (nin_trails.glsl, before this shader): the picture leaves trails that sink,
//                   smear and swirl apart in a drifting noise field, with a strong heat-haze warp
//   act 3 SCRIM   - the picture as if projected on stacked translucent scrims (Peel It Back): fainter copies behind,
//                   the front fabric moving in the air, heat-haze warp, a Pepper's-ghost reflection
// In every act strong hits leave "Copy of A" echoes: delayed copies that drift out and fade. Nothing flashes: noise
// keeps the picture's own brightness, and every change is smoothed.
// input 0 = the picture (ink_layer/OUT), inputs 1, 2 = the same picture some frames ago (Cache Select TOPs).
uniform vec4 uA;   // time (s), Amount, level (track, smoothed), hit pulse
uniform vec4 uS;   // Scrim (depth layers), Ripple (fabric moving in the air), Parallax, Ghost (Pepper's ghost)
uniform vec4 uE;   // Echo amount, echo envelope (0..1, set by a hit, decays), echo age (s since the hit), Echodrift
uniform vec4 uD;   // drift direction x, y (changes on each hit), Haze, Darkness
uniform vec4 uN;   // Static, Melt (used by nin_trails.glsl), Warp (heat haze), frame
out vec4 fragColor;

float h21(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y);
}
float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 4; i++) { s += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; } return s / 0.9375; }
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }

vec3 tex(int i, vec2 uv) {
	uv = clamp(uv, vec2(0.001), vec2(0.999));
	if (i == 0) return texture(sTD2DInputs[0], uv).rgb;
	if (i == 1) return texture(sTD2DInputs[1], uv).rgb;
	return texture(sTD2DInputs[2], uv).rgb;
}
vec3 layer(int i, vec2 uv, float scale, vec2 off, float blur) {
	vec2 q = (uv - 0.5) / scale + 0.5 + off;
	vec3 acc = vec3(0.0);
	for (int k = 0; k < 8; k++) {
		float a = float(k) * 2.39996;
		vec2 o = vec2(cos(a), sin(a) * 0.5625) * blur * sqrt((float(k) + 0.5) / 8.0);
		acc += tex(i, q + o);
	}
	return acc / 8.0;
}

void main() {
	vec2 uv = vUV.st;
	vec2 R = uTDOutputInfo.res.zw;
	float t = uA.x, amt = uA.y, lvl = uA.z, pulse = uA.w;
	float scrim = uS.x, rip = uS.y, par = uS.z, ghost = uS.w;
	float stat = uN.x, warp = uN.z, frame = uN.w;
	float env = uE.y, age = uE.z;
	float paper = smoothstep(0.35, 0.75, luma(layer(0, vec2(0.5), 1.0, vec2(0.0), 0.45)));

	// ---------------- where we look: heat haze (warp), fabric folds (ripple), torn rows and vertical roll (static)
	vec2 p = uv;
	vec2 hw = vec2(fbm(uv * vec2(2.5, 4.0) + vec2(0.0, t * 0.35)), fbm(uv * vec2(2.5, 4.0) + vec2(5.2, t * 0.3))) - 0.5;
	p += hw * 0.018 * warp * (0.6 + 0.6 * lvl);
	vec2 w = vec2(fbm(vec2(uv.y * 2.2, t * 0.09)), fbm(vec2(uv.x * 1.6 + 4.0, t * 0.07))) - 0.5;
	p += w * vec2(0.022, 0.014) * rip * (0.7 + 0.8 * lvl);
	float tearBand = smoothstep(0.62, 0.9, vnoise(vec2(uv.y * 9.0, t * 1.3)));
	float row = floor(uv.y * R.y / 3.0);
	float tear = (h21(vec2(row, floor(t * 12.0))) - 0.5) * (0.004 + 0.05 * env) * tearBand;
	p.x += tear * stat * 2.0;
	p.y = fract(p.y + stat * 0.02 * sin(t * 0.21) * smoothstep(0.4, 1.0, vnoise(vec2(t * 0.15, 3.0))));

	vec3 col = tex(0, p);
	float fold = fbm(vec2(uv.x * 3.0 + t * 0.05, uv.y * 0.8));
	col = mix(col, col * (1.0 + (fold - 0.5) * 0.6), 0.4 * rip);

	// ---------------- act 3: SCRIM - fainter copies further back, sway, Pepper's ghost
	vec3 seen = col;
	if (scrim > 0.001 || ghost > 0.001) {
		vec2 sway = vec2(sin(t * 0.13), cos(t * 0.097)) * 0.014 + vec2(0.3, 1.0) * pulse * 0.02;
		vec3 mid = layer(0, p, 0.93, sway * par, 0.003);
		vec3 back = layer(0, p, 0.84, sway * 2.4 * par, 0.008);
		float kM = 0.55 * scrim, kB = 0.35 * scrim;
		vec3 midP = mix(vec3(1.0), mid, kM), backP = mix(vec3(1.0), back, kB);
		seen = mix(max(seen, max(mid * kM, back * kB)), min(seen, min(midP, backP)), paper);
		vec3 g = layer(0, p, 1.08, vec2(-0.018, 0.012) - sway * 1.5 * par, 0.005);
		float kG = 0.32 * ghost;
		seen = mix(max(seen, g * kG), min(seen, mix(vec3(1.0), g, kG)), paper);
	}

	// ---------------- Copy of A: delayed copies drift out and fade after a hit (all acts)
	if (uE.x > 0.0 && env > 0.002) {
		vec2 dir = uD.xy;
		vec3 e = vec3(0.0); float ws = 0.0;
		for (int k = 1; k <= 3; k++) {
			float fk = float(k);
			vec2 off = dir * (0.012 * fk + 0.05 * age * fk) * uE.w;
			float wk = env * (1.0 - 0.22 * fk);
			e += tex(min(k, 2), uv - off * (k == 3 ? 1.35 : 1.0)) * wk; ws += wk;
		}
		e /= max(ws, 1e-4);
		float a = clamp(ws / 3.0, 0.0, 1.0) * uE.x;
		seen = mix(seen, mix(max(seen, e), min(seen, e), paper), a * 0.85);
	}

	// ---------------- act 1: STATIC - the signal dissolves into fine monochrome noise in drifting bands
	if (stat > 0.001) {
		float L = luma(seen);
		vec2 px = floor(uv * R);
		float n = h21(px + vec2(frame * 17.0, frame * 7.0));
		float n2 = h21(floor(px / 2.0) + vec2(frame * 3.0, 11.0));
		float grain = mix(n, n2, 0.4);
		float bands = smoothstep(0.35, 0.8, fbm(vec2(uv.y * 6.0 - t * 0.6, t * 0.2)));
		// a slow rolling bar of lost signal, and thin rows where the line is smeared sideways
		float yb = fract(0.15 - t * 0.045);
		float bar = exp(-pow((uv.y - yb) / 0.035, 2.0)) + exp(-pow((uv.y - fract(yb + 0.47)) / 0.015, 2.0)) * 0.6;
		float m = stat * clamp(0.25 + 0.65 * bands * (0.4 + 0.6 * lvl) + 0.8 * bar + 0.4 * env * tearBand, 0.0, 0.95);
		float hrow = floor(uv.y * R.y / 2.0);
		float smear = step(0.965 - 0.04 * env, h21(vec2(hrow, floor(t * 6.0))));
		vec3 stretched = tex(0, vec2(0.5 + (p.x - 0.5) * 0.08, p.y));
		seen = mix(seen, stretched, smear * stat * 0.8);
		// noise around the picture's own brightness (a little above it in the dark): it breaks up, it never flashes
		vec3 noisy = vec3(clamp(L + (grain - 0.42) * 0.7, 0.0, 1.0));
		seen = mix(seen, noisy, m);
		seen *= 1.0 - 0.10 * stat * (0.5 + 0.5 * sin(uv.y * R.y * 1.5708));       // scanlines
	}

	// ---------------- haze lifts the darks a little; darkness sinks the edges
	float hz = fbm(uv * vec2(1.4, 2.4) + vec2(t * 0.01, -t * 0.02));
	seen = mix(seen, seen + vec3(0.05) * hz * (1.0 - paper), uD.z);
	vec2 v = (uv - 0.5) * vec2(1.0, 1.4);
	seen *= mix(1.0, smoothstep(0.85, 0.25, length(v)), uD.w * (1.0 - 0.6 * paper));

	fragColor = TDOutputSwizzle(vec4(mix(tex(0, uv), clamp(seen, 0.0, 1.0), amt), 1.0));
}
