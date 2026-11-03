// NIN Stage - the last layer of TDA: the picture as if projected on stacked translucent scrims (Peel It Back),
// plus "Copy of A" echoes: on strong hits the scene leaves delayed, drifting copies of itself that fade out, and the
// linear light rig: thin sheets of light rising from the floor, or slowly turning blades, seen in haze; hits run a
// soft chase along them. Nothing flashes: every light change is smoothed.
// input 0 = the picture (ink_layer/OUT), inputs 1, 2 = the same picture some frames ago (Cache Select TOPs);
// the third copy is the oldest one again, drifted further (a GLSL TOP here takes three inputs).
uniform vec4 uA;   // time (s), Amount, transient level (track A), transient pulse (track A)
uniform vec4 uS;   // Scrim (depth layers), Ripple (fabric moving in the air), Parallax, Ghost (Pepper's ghost)
uniform vec4 uE;   // Echo amount, echo envelope (0..1, set by a hit, decays), echo age (s since the hit), Echodrift
uniform vec4 uD;   // drift direction x, y (changes on each hit), Haze, Darkness
uniform vec4 uL;   // Lines (sheets of light amount), Linemode (0 = sheets rising from the floor, 1 = rotating blades), chase phase, level (smoothed)
uniform vec4 uK;   // Linecount, Linewidth, blade angle, 0
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
// a soft (out of focus) look at input i, scaled about the centre: a scrim further back
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
	float t = uA.x, amt = uA.y, lvl = uA.z, pulse = uA.w;
	float scrim = uS.x, rip = uS.y, par = uS.z, ghost = uS.w;

	// is the picture positive (white paper) or negative (dark)? from a wide sample around the centre
	float paper = smoothstep(0.35, 0.75, luma(layer(0, vec2(0.5), 1.0, vec2(0.0), 0.45)));
	// the front scrim moves in the air: slow, wide folds that bend the picture (more with track 1)
	vec2 w = vec2(fbm(vec2(uv.y * 2.2, t * 0.09)), fbm(vec2(uv.x * 1.6 + 4.0, t * 0.07))) - 0.5;
	float fold = fbm(vec2(uv.x * 3.0 + t * 0.05, uv.y * 0.8));
	vec2 front = uv + w * vec2(0.022, 0.014) * rip * (0.7 + 0.8 * lvl);
	vec3 col = tex(0, front);
	// light catches the folds of the fabric: a slow sheen / shadow across the scrim
	col = mix(col, col * (1.0 + (fold - 0.5) * 0.6), 0.4 * rip);

	// the scrims behind: the same picture, smaller, softer and paler (or dimmer in the dark), swaying slowly and
	// pushed by the hits - they show as grey shadows of the scene behind the front one
	vec2 sway = vec2(sin(t * 0.13), cos(t * 0.097)) * 0.014 + vec2(0.3, 1.0) * pulse * 0.02;
	vec3 mid = layer(0, uv, 0.93, sway * par, 0.003);
	vec3 back = layer(0, uv, 0.84, sway * 2.4 * par, 0.008);
	vec3 seen = col;
	float kM = 0.55 * scrim, kB = 0.35 * scrim;
	// on white paper the far scrims can only add (fainter) ink: darken; in the dark picture they add (dimmer) light
	vec3 midP = mix(vec3(1.0), mid, kM), backP = mix(vec3(1.0), back, kB);
	vec3 midD = mid * kM, backD = back * kB;
	seen = mix(max(seen, max(midD, backD)), min(seen, min(midP, backP)), paper);
	// Pepper's ghost: a faint reflection of the scene, larger and offset, floating in front
	vec3 g = layer(0, uv, 1.08, vec2(-0.018, 0.012) - sway * 1.5 * par, 0.005);
	float kG = 0.32 * ghost;
	seen = mix(max(seen, g * kG), min(seen, mix(vec3(1.0), g, kG)), paper);

	// Copy of A: three delayed copies drift out and fade after a hit
	float env = uE.y, age = uE.z;
	if (uE.x > 0.0 && env > 0.002) {
		vec2 dir = uD.xy;
		vec3 e = vec3(0.0); float ws = 0.0;
		for (int k = 1; k <= 3; k++) {
			float fk = float(k);
			vec2 off = dir * (0.012 * fk + 0.05 * age * fk) * uE.w;
			float wk = env * (1.0 - 0.22 * fk);
			vec3 c = tex(min(k, 2), uv - off * (k == 3 ? 1.35 : 1.0));
			e += c * wk; ws += wk;
		}
		e /= max(ws, 1e-4);
		float a = clamp(ws / 3.0, 0.0, 1.0) * uE.x;
		// the copies are blended so their ink shows over the paper (or their light over the dark), never flashing
		vec3 lighter = max(seen, e), darker = min(seen, e);
		seen = mix(seen, mix(lighter, darker, paper), a * 0.85);
	}

	// sheets of light (the linear rig): seen through haze, grey, never flashing
	if (uL.x > 0.001) {
		float n = max(uK.x, 2.0), wdt = max(uK.y, 0.0005);
		float hzv = 0.35 + 0.65 * fbm(uv * vec2(3.0, 1.2) + vec2(t * 0.03, -t * 0.08));      // the light is seen in haze
		// A: thin vertical sheets rising from the floor, as high as the music is loud, a chase running along them
		float sx = uv.x * n;
		float i = floor(sx + 0.5);
		float dx = abs(sx - i) / n;
		float rise = smoothstep(0.15 + 0.85 * uL.w, 0.0, uv.y * 0.9);
		float chase = 0.35 + 0.65 * pow(0.5 + 0.5 * sin(i * 1.1 - uL.z), 3.0);
		float sheets = exp(-dx / wdt) * rise * chase;
		sheets += 0.25 * exp(-abs(uv.y - 0.06) / (wdt * 4.0)) * (0.5 + 0.5 * chase);           // the light line on the floor
		// B: blades turning slowly about the centre (pairs of thin lines), like the panning linear fixtures
		vec2 p = (uv - 0.5) * vec2(0.5625, 1.0);
		float bl = 0.0;
		for (int k = 0; k < 3; k++) {
			float a = uK.z + float(k) * 1.0472;
			vec2 dir = vec2(cos(a), sin(a));
			float d = abs(dot(p, vec2(-dir.y, dir.x)));
			float along = dot(p, dir);
			bl += 1.6 * exp(-d / (wdt * 0.9)) * smoothstep(0.62, 0.05, abs(along)) * (0.45 + 0.55 * pow(0.5 + 0.5 * sin(float(k) * 2.1 - uL.z), 2.0));
		}
		float Lr = mix(sheets, bl, clamp(uK.w + uL.y, 0.0, 1.0)) * hzv * uL.x * (0.35 + 0.65 * uL.w);
		Lr = clamp(Lr, 0.0, 1.2);
		// in the dark picture the rig adds grey light; on white paper it lays thin shadows
		seen = mix(seen + vec3(0.55) * Lr, seen * (1.0 - 0.45 * clamp(Lr, 0.0, 1.0)), paper);
	}

	// haze: a soft veil that lifts the darks a little; darkness: the edges sink into black
	float hz = fbm(uv * vec2(1.4, 2.4) + vec2(t * 0.01, -t * 0.02));
	seen = mix(seen, seen + vec3(0.05) * hz * (1.0 - paper), uD.z);
	vec2 v = (uv - 0.5) * vec2(1.0, 1.4);
	seen *= mix(1.0, smoothstep(0.85, 0.25, length(v)), uD.w * (1.0 - 0.6 * paper));

	fragColor = TDOutputSwizzle(vec4(mix(tex(0, uv), seen, amt), 1.0));
}
