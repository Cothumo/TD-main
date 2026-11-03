// Thorns - after the ink, before the NIN stage (ink_layer -> thorns -> nin_stage).
//   - thorn web: sharp strands with small barbs strung between the dense spots of the Ambient Ink, some in focus,
//     some soft as if out of focus (depth). Strongest in the inverted (white) picture, where they read as black
//     barbed drawing; faint pale strands in the dark picture.
//   - barbed bursts: on hits, spiky star-shaped thorn marks shoot out where the ink is, smeared along the drift of
//     the echoes, and fade within half a second.
// input 0 = the picture (ink_layer/OUT), input 1 = the ink alone (ink_layer/ink: ink on white paper)
uniform vec4 uA;   // time (s), Web, Bursts, Webcell (px)
uniform vec4 uB;   // hit envelope, seconds since the hit, hit seed, drift angle (rad)
uniform vec4 uC;   // Barbs, Depth (out-of-focus strands), Burstsize (px), Inkthreshold
out vec4 fragColor;
#define PI 3.14159265
float h21(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
float inkd(vec2 uv) { return 1.0 - luma(texture(sTD2DInputs[1], clamp(uv, vec2(0.001), vec2(0.999))).rgb); }
float segd(vec2 p, vec2 a, vec2 b, out float h) { vec2 pa = p - a, ba = b - a; h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-4), 0.0, 1.0); return length(pa - ba * h); }

// the web's node in a cell: a slowly drifting point, alive where the ink is dense
vec3 wnode(vec2 cell, float cs, float t, vec2 RS) {
	vec2 r = vec2(h21(cell), h21(cell.yx + 4.1));
	vec2 n = (cell + 0.2 + 0.6 * r + 0.18 * vec2(sin(t * 0.13 + r.x * 6.0), cos(t * 0.11 + r.y * 6.0))) * cs;
	float w = smoothstep(uC.w, uC.w + 0.25, inkd(n / RS));
	return vec3(n, w);
}
// a strand between two nodes: thin, with barbs every few pixels; z = depth (0 sharp .. 1 soft)
float strand(vec2 p, vec2 a, vec2 b, float z, float seed) {
	float h;
	float d = segd(p, a, b, h);
	float L = length(b - a);
	float wdt = 0.6 + 2.6 * z * uC.y;
	float s = (1.0 - smoothstep(wdt * 0.5, wdt * 0.5 + 0.8 + 2.0 * z * uC.y, d)) * mix(1.0, 0.4, z * uC.y);
	// barbs: short ticks leaning along the strand, alternating sides
	if (uC.x > 0.0 && L > 1.0) {
		vec2 dir = (b - a) / L, nrm = vec2(-dir.y, dir.x);
		float sp = 9.0 + 6.0 * h21(vec2(seed, 1.0));
		float k = floor(h * L / sp + 0.5);
		vec2 q = a + dir * k * sp;
		float side = mod(k, 2.0) * 2.0 - 1.0;
		vec2 tip = q + (nrm * side * 0.8 - dir * 0.6) * (3.0 + 3.0 * h21(vec2(k, seed))) * uC.x;
		float hb;
		float db = segd(p, q, tip, hb);
		s = max(s, (1.0 - smoothstep(wdt * 0.4 * (1.0 - hb), wdt * 0.4 * (1.0 - hb) + 0.9, db)) * step(0.35, h21(vec2(k, seed + 3.0))) * mix(1.0, 0.4, z * uC.y));
	}
	return s;
}

void main() {
	vec2 uv = vUV.st;
	float t = uA.x;
	vec2 RS = uTDOutputInfo.res.zw;
	vec2 p = uv * RS;
	vec3 col = texture(sTD2DInputs[0], uv).rgb;
	float paper = smoothstep(0.35, 0.75, (luma(texture(sTD2DInputs[0], vec2(0.2, 0.25)).rgb) + luma(texture(sTD2DInputs[0], vec2(0.8, 0.75)).rgb)
	              + luma(texture(sTD2DInputs[0], vec2(0.5, 0.1)).rgb)) / 3.0);
	float mark = 0.0;

	// ---- thorn web
	if (uA.y > 0.001) {
		float cs = max(uA.w, 20.0);
		vec2 c0 = floor(p / cs);
		vec3 N[16];
		for (int j = 0; j < 4; j++) for (int i = 0; i < 4; i++)
			N[j * 4 + i] = wnode(c0 + vec2(float(i - 1), float(j - 1)), cs, t, RS);
		float web = 0.0;
		for (int j = 0; j < 3; j++) for (int i = 0; i < 3; i++) {
			vec3 a = N[j * 4 + i];
			if (a.z < 0.05) continue;
			vec2 cell = c0 + vec2(float(i - 1), float(j - 1));
			for (int k = 0; k < 3; k++) {
				vec3 b = k == 0 ? N[j * 4 + i + 1] : (k == 1 ? N[(j + 1) * 4 + i] : N[(j + 1) * 4 + i + 1]);
				float sd = h21(cell * 3.1 + float(k) * 7.3);
				if (b.z < 0.05 || sd < 0.3) continue;
				float z = h21(cell * 1.7 + float(k));
				web = max(web, strand(p, a.xy, b.xy, z, sd * 100.0) * min(a.z, b.z));
			}
		}
		mark = max(mark, web * uA.y * (0.4 + 0.6 * paper));
	}

	// ---- barbed bursts on hits
	if (uA.z > 0.001 && uB.x > 0.01) {
		float age = uB.y;
		float grow = 1.0 - exp(-age * 14.0);
		float fade = exp(-age / 0.5) * uB.x;
		vec2 dd = vec2(cos(uB.w), sin(uB.w));
		float bst = 0.0;
		for (int b = 0; b < 5; b++) {
			float fb = float(b);
			vec2 c = vec2(h21(vec2(uB.z, fb)), h21(vec2(fb, uB.z + 1.3))) * RS;
			float w = 0.35 + 0.65 * smoothstep(uC.w, uC.w + 0.25, inkd(c / RS));   // stronger where the ink is
			vec2 v = p - c;
			// smear along the drift (motion blur): squeeze the drift component
			float along = dot(v, dd);
			v -= dd * along * 0.45 * smoothstep(0.0, 0.3, age);
			float r = length(v);
			float R = uC.z * (0.6 + 0.6 * h21(vec2(fb, uB.z + 7.0))) * grow;
			if (r > R * 1.2 + 4.0) continue;
			float ang = atan(v.y, v.x);
			float s = 0.0;
			for (int k = 0; k < 11; k++) {
				float fk = float(k);
				float sa = (fk + 0.6 * h21(vec2(fk, fb + uB.z))) / 11.0 * 2.0 * PI;
				float sl = R * (0.35 + 0.65 * h21(vec2(fk + 2.0, fb + uB.z)));
				vec2 sdir = vec2(cos(sa), sin(sa));
				float a2 = dot(v, sdir);
				float pp = abs(dot(v, vec2(-sdir.y, sdir.x)));
				float taper = 1.0 - clamp(a2 / max(sl, 1.0), 0.0, 1.0);
				s = max(s, step(0.0, a2) * step(a2, sl) * (1.0 - smoothstep(0.3 + 2.2 * taper, 1.2 + 2.2 * taper, pp)));
			}
			s = max(s, 1.0 - smoothstep(2.0, 4.0 + 2.0 * grow, r));                  // the dense core
			bst = max(bst, s * w);
		}
		mark = max(mark, bst * fade * uA.z);
	}

	// black barbed drawing on white paper, faint pale strands in the dark
	mark = clamp(mark, 0.0, 1.0);
	col = mix(col + vec3(0.32) * mark, col * (1.0 - 0.85 * mark), paper);
	fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
