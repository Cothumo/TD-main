// ---- holo_common.glsl - shared by every shader of /project1/artist_hologram (the build script puts it in front)
// UV is TouchDesigner's: x to the right, y UP. 'img' means image rows (y down), like the photo.
uniform vec4 uTime;   // t (s, inside the loop), Loop (s), dt (s), absolute time (s, keeps running)
uniform vec4 uApp;    // appearance 1: start (s), strength; appearance 2: start (s), strength
uniform vec4 uEnv;    // Rise, Hold, Fall (s), external hit envelope (< 0 = use the loop's bursts)
uniform vec4 uBur;    // burst 1, burst 2 (s), frame number, 0

const float TAU = 6.28318531;
const float K720 = 1.0 / 720.0;          // 1 px of a 720 high frame, in UV (the video's pixel sizes are for 720)
const float HEADW = 0.6157;              // right edge of the head in the frame (UV x)

float h21(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y);
}
float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * vnoise(p); p = p * 2.03 + vec2(17.1, 9.7); a *= 0.5; } return s / 0.96875; }

uvec4 pcg4d(uvec4 v) {
	v = v * 1664525u + 1013904223u;
	v.x += v.y * v.w; v.y += v.z * v.x; v.z += v.x * v.y; v.w += v.y * v.z;
	v ^= v >> 16u;
	v.x += v.y * v.w; v.y += v.z * v.x; v.z += v.x * v.y; v.w += v.y * v.z;
	return v;
}
vec4 rnd4(uint id, uint salt) { return vec4(pcg4d(uvec4(id, salt, id ^ 0x9E3779B9u, salt * 7u + 1u))) * (1.0 / 4294967295.0); }

float loopPhase() { return TAU * uTime.x / max(uTime.y, 0.1); }

// the face surfaces now and then: eased in over Rise, lingers Hold, sinks back over Fall (periodic in the loop)
float envOne(float t, float t0, float amp) {
	float R = max(uEnv.x, 0.01), H = max(uEnv.y, 0.0), F = max(uEnv.z, 0.01);
	float d = mod(t - t0, uTime.y), v = 0.0;
	if (d < R) v = pow(smoothstep(0.0, R, d), 1.7);
	else if (d < R + H) v = 1.0;
	else if (d < R + H + F) v = pow(1.0 - smoothstep(R + H, R + H + F, d), 1.3);
	return amp * v;
}
float presence(float t) { return max(envOne(t, uApp.x, uApp.y), envOne(t, uApp.z, uApp.w)); }

// the unstable moments: jump up, decay (periodic in the loop)
float burstEnv(float t, float tau) {
	float e = 0.0, T = uTime.y;
	for (int k = 0; k < 2; k++) {
		float d = mod(t - (k == 0 ? uBur.x : uBur.y), T);
		if (d < T * 0.9) e = max(e, (1.0 - exp(-d / 0.06)) * exp(-d / tau) / 0.85);
	}
	return min(e, 1.0);
}
float hitEnv(float t) { return uEnv.w >= 0.0 ? clamp(uEnv.w, 0.0, 1.0) : burstEnv(t, 0.45); }
float gustEnv(float t) { return uEnv.w >= 0.0 ? clamp(uEnv.w, 0.0, 1.0) : burstEnv(t, 0.7); }

// the head floats a little (UV, y up)
float bobUV(float t) { float th = loopPhase(); return -(5.0 * sin(th) + 2.0 * sin(2.0 * th + 1.0)) / 1080.0; }

// periodic curl-noise flow (UV per second): three octaves, drifting on circles in noise space
float psiN(vec2 p, float f, float r, float ph) { float th = loopPhase(); return vnoise(p * f + r * vec2(cos(th + ph), sin(th + ph)) + ph * 7.3); }
vec2 curlFlow(vec2 p, float turb) {
	vec2 v = vec2(0.0);
	float fq[3] = float[3](5.0, 14.0, 36.0), am[3] = float[3](0.062, 0.056, 0.031);
	for (int o = 0; o < 3; o++) {
		float e = 0.25 / fq[o];
		float dx = psiN(p + vec2(e, 0.0), fq[o], 0.6, float(o)) - psiN(p - vec2(e, 0.0), fq[o], 0.6, float(o));
		float dy = psiN(p + vec2(0.0, e), fq[o], 0.6, float(o)) - psiN(p - vec2(0.0, e), fq[o], 0.6, float(o));
		v += vec2(dy, -dx) / (2.0 * e * fq[o]) * am[o] * 1.6;
	}
	return v * turb;
}

// the head's own particles: a fixed life cycle per particle (rest on the head for 'hold', then fly with the stream)
// returns L, age, hold, generation; rp = its resting point for this generation (UV, before the bob)
vec4 headCycle(uint id, float tAbs, float holdBase, out vec2 rp) {
	vec4 h = rnd4(id, 31u);
	float L = mix(3.0, 6.5, h.x);                                  // one life: rest + flight (s)
	float tt = tAbs + h.y * L;
	float gen = floor(tt / L);
	float age = tt - gen * L;
	vec4 g = rnd4(id * 7u + uint(gen) * 131u, 57u);
	rp = vec2(g.x * (HEADW + 0.02), g.y);
	float xn = clamp(rp.x / HEADW, 0.0, 1.0);
	// the back of the head lets go first (like the video: Hold x (0.5 + 0.7 (1 - x)^1.1) x random)
	float hold = holdBase * (0.3 + 0.7 * pow(1.0 - xn, 1.1) + 0.2) * (0.55 + 0.9 * g.z);
	hold = clamp(hold, 0.15 * L, L - 0.8);
	return vec4(L, age, hold, gen);
}
// ---- end of holo_common.glsl
