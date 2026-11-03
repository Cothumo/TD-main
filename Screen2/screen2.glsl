// Screen 2 - the live silhouette on its own screen, backlit haze: the performer as a dark figure against one soft
// light far behind drifting haze; the haze flows round the body, the outline catches the light.
// Signal breakup, NIN style:
//   - time slicing: each row of the figure comes from a slightly different moment - movement smears it through time
//   - buffer stutter: on strong hits the figure loops its last few frames for a moment, like a stuck video buffer
//   - scan-line displacement: the figure drawn as horizontal lines lifted by the camera picture (analog video synth)
//   - traces where it moved break up into noise and dissolve, older ghosts drift behind it
//   - interlace drift (odd / even lines pull apart while it moves) and snow where it moved; rows tear sideways
//   - a failing analog TV all the time (Ambient), more when it moves and on hits: a tracking band rolls through,
//     the sync wobbles, the vertical hold slips now and then, faint snow, thin dropouts streak across
// The pads (Stems) thicken the haze, the music's level breathes the light. Grey only.
// input 0 = silhouette now (r = body, g = trail), input 1 = its history (2D texture array, Historysize frames),
// input 2 = the camera picture
uniform vec4 uA;   // time (s), Figure (0..1), Echoes (0..1), Mirror (0/1)
uniform vec4 uB;   // pads (0..1), level (0..1), Haze, Lightsize
uniform vec4 uC;   // light x, light y, Scale, Rim
uniform vec4 uD;   // X, Y (figure offset), Flow, Light (brightness)
uniform vec4 uE;   // Noise (traces), Tear, Ghosts, Scanlines
uniform vec4 uF;   // Detail, Interlace, motion (0..1), Snow
uniform vec4 uH;   // Lines (scan-line figure), Lineheight, Linespacing (px), -
uniform vec4 uI;   // Timeslice, stutter on (0/1), stutter base frame, stutter loop length (frames)
uniform vec4 uJ;   // current frame, history size (frames), hit envelope, -
uniform vec4 uG;   // Chaos (analog TV), Ambient (how much of it runs all the time, even when nothing moves), -, -
uniform vec4 uK;   // Track (tracking overlay), Trackcell (px between tracked points), -, -
out vec4 fragColor;
float h21(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y);
}
float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; } return s / 0.96875; }
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }

// frame position -> camera picture position (the camera fills the screen, scaled / moved / mirrored); z = inside
vec3 cam(vec2 uv) {
	vec2 r0 = uTD2DInfos[0].res.zw;
	float Ac = r0.x / max(r0.y, 1.0);
	float Ao = uTDOutputInfo.res.z / uTDOutputInfo.res.w;
	vec2 c = uv - 0.5 - uD.xy;
	c /= max(uC.z, 0.05);
	c.x *= Ao / max(Ac, 0.01);
	c += 0.5;
	if (uA.w > 0.5) c.x = 1.0 - c.x;
	vec2 e = smoothstep(0.0, 0.04, c) * smoothstep(0.0, 0.04, 1.0 - c);
	float inside = (c.x < 0.0 || c.y < 0.0 || c.x > 1.0 || c.y > 1.0) ? 0.0 : e.x * e.y;
	return vec3(c, inside);
}
float HS() { return max(uJ.y, 1.0); }
// the silhouette 'age' frames ago (0 = now) from the history
vec2 silAt(vec2 uv, float age) {
	vec3 c = cam(uv);
	if (c.z <= 0.0) return vec2(0.0);
	age = clamp(floor(age + 0.5), 0.0, HS() - 2.0);
	float slice = mod(uJ.x - age, HS());
	return texture(sTD2DArrayInputs[0], vec3(c.xy, slice)).rg * c.z;
}
vec2 sil(vec2 uv) { vec3 c = cam(uv); return c.z > 0.0 ? texture(sTD2DInputs[0], c.xy).rg * c.z : vec2(0.0); }
// ---- tracking overlay: points locked onto the body's outline, boxed, labelled with fake data, joined by hairlines
float segd(vec2 p, vec2 a, vec2 b) { vec2 pa = p - a, ba = b - a; float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-4), 0.0, 1.0); return length(pa - ba * h); }
// a point of the cell snapped onto the outline (2 Newton steps on the mask); z = 1 if it found the outline
vec3 tnode(vec2 cell, float cs, float tk, vec2 RS) {
	vec2 n = (cell + vec2(h21(cell + tk * 0.137), h21(cell.yx + 3.7 + tk * 0.071))) * cs;
	for (int it = 0; it < 3; it++) {
		float h = it == 0 ? cs * 0.5 : (it == 1 ? 8.0 : 3.0);     // wide first, to find an outline anywhere in the cell
		float m = sil(n / RS).r;
		vec2 g = vec2(sil((n + vec2(h, 0.0)) / RS).r - sil((n - vec2(h, 0.0)) / RS).r,
		              sil((n + vec2(0.0, h)) / RS).r - sil((n - vec2(0.0, h)) / RS).r) / (2.0 * h);
		float gl = dot(g, g);
		if (gl < 1e-7) return vec3(n, 0.0);
		n -= (m - 0.5) * g / gl;
	}
	float home = step(length(n / cs - (cell + 0.5)), 0.9);          // it must stay near its own cell
	float m = sil(n / RS).r;
	float sel = step(0.3, h21(cell * 1.31 + tk * 0.29));            // not every outline point is tracked
	return vec3(n, home * sel * (1.0 - smoothstep(0.15, 0.35, abs(m - 0.5))));
}
float tracking(vec2 uv, vec2 RS, float t, float cs) {
	vec2 p = uv * RS;
	vec2 c0 = floor(p / cs);
	float tk = floor(t * 6.0);
	vec3 N[16];
	for (int j = 0; j < 4; j++) for (int i = 0; i < 4; i++)
		N[j * 4 + i] = tnode(c0 + vec2(float(i - 1), float(j - 1)), cs, tk, RS);
	float v = 0.0;
	for (int j = 0; j < 3; j++) for (int i = 0; i < 3; i++) {
		vec3 a = N[j * 4 + i];
		if (a.z < 0.05) continue;
		vec2 cell = c0 + vec2(float(i - 1), float(j - 1));
		vec2 n = a.xy;
		// box
		float bs = 5.0 + 4.0 * h21(cell + 9.1);
		vec2 q = abs(p - n);
		float box = (1.0 - smoothstep(0.5, 1.2, abs(max(q.x, q.y) - bs)));
		// label: a short row of tiny bars to the right of the box (like coordinates); sometimes a column of data above
		vec2 l = p - n - vec2(bs + 3.0, -2.0);
		float gi = floor(l.x / 3.0);
		float lab = step(0.0, l.x) * step(l.x, 3.0 * (3.0 + floor(4.0 * h21(cell + 2.2)))) * step(0.0, l.y) * step(l.y, 4.0)
		          * step(1.0, mod(l.x, 3.0)) * step(0.3, h21(vec2(gi, cell.x + cell.y * 7.0 + tk)));
		vec2 cl = p - n - vec2(-1.0, bs + 3.0);
		float colm = step(0.7, h21(cell + 5.5)) * step(0.0, cl.x) * step(cl.x, 2.0 + 6.0 * h21(vec2(floor(cl.y / 3.0), cell.x + tk)))
		           * step(0.0, cl.y) * step(cl.y, 30.0) * step(1.0, mod(cl.y, 3.0));
		v = max(v, a.z * max(box, max(lab, colm) * 0.8));
		// hairlines to the tracked neighbours (right, up, diagonal)
		vec3 b1 = N[j * 4 + i + 1], b2 = N[(j + 1) * 4 + i], b3 = N[(j + 1) * 4 + i + 1];
		if (b1.z > 0.05) v = max(v, (1.0 - smoothstep(0.3, 0.9, segd(p, n, b1.xy))) * min(a.z, b1.z) * 0.8);
		if (b2.z > 0.05) v = max(v, (1.0 - smoothstep(0.3, 0.9, segd(p, n, b2.xy))) * min(a.z, b2.z) * 0.8);
		if (b3.z > 0.05 && h21(cell + 7.7) > 0.5) v = max(v, (1.0 - smoothstep(0.3, 0.9, segd(p, n, b3.xy))) * min(a.z, b3.z) * 0.6);
	}
	return v;
}
float relief(vec2 uv) {
	vec3 c = cam(uv);
	if (c.z <= 0.0) return 0.0;
	vec2 o = uTD2DInfos[1].res.xy * 2.5;
	float l = luma(texture(sTD2DInputs[1], c.xy).rgb), m = 0.0;
	m += luma(texture(sTD2DInputs[1], c.xy + vec2(o.x, 0.0)).rgb) + luma(texture(sTD2DInputs[1], c.xy - vec2(o.x, 0.0)).rgb);
	m += luma(texture(sTD2DInputs[1], c.xy + vec2(0.0, o.y)).rgb) + luma(texture(sTD2DInputs[1], c.xy - vec2(0.0, o.y)).rgb);
	m += luma(texture(sTD2DInputs[1], c.xy + o * 2.0).rgb) + luma(texture(sTD2DInputs[1], c.xy - o * 2.0).rgb);
	return (l - m / 6.0) * c.z;
}

void main() {
	vec2 uv = vUV.st;
	float t = uA.x;
	vec2 RS = uTDOutputInfo.res.zw;
	float asp = RS.x / RS.y;
	float NOI = uE.x, TEAR = uE.y, GH = uE.z * uA.z;
	float mot = clamp(uF.z * 6.0, 0.0, 1.0);
	float hitE = clamp(uJ.z, 0.0, 1.0);

	// ---- where it moved right now
	vec2 s_ = sil(uv);
	float moved = clamp(s_.g - s_.r, 0.0, 1.0);
	// rows tear sideways while it moves; odd and even lines drift apart
	float row = floor(uv.y * 240.0);
	float tk = floor(t * 7.0);
	float band = smoothstep(0.78, 1.0, h21(vec2(row, tk))) + 0.35 * smoothstep(0.5, 1.0, h21(vec2(floor(uv.y * 30.0), tk + 7.0)));
	float tear = (h21(vec2(row, tk + 3.1)) - 0.5) * 0.05 * TEAR * band * smoothstep(0.02, 0.4, moved + 0.6 * silAt(uv, 6.0).r);
	float CH = uG.x, AMB = uG.y;
	tear += (h21(vec2(row, tk + 5.3)) - 0.5) * 0.03 * TEAR * band * AMB * CH;                    // the figure tears a little even when still
	float il = (mod(floor(uv.y * RS.y), 2.0) - 0.5) * 0.006 * uF.y * (0.15 + AMB * 0.5 + mot) * (0.4 + moved * 1.5 + AMB * 0.4);
	// ---- analog TV: tracking band rolling down, sync wobble, vertical hold slipping now and then
	float drive = max(AMB, max(mot, hitE));
	float by = fract(-t * 0.045 + 0.3 * sin(t * 0.013));
	float bdy = abs(uv.y - by); bdy = min(bdy, 1.0 - bdy);
	float bandT = (1.0 - smoothstep(0.0, 0.045 + 0.04 * mot, bdy)) * CH * (0.3 + 0.7 * drive);
	float wob = sin(uv.y * 38.0 + t * 3.1) * sin(uv.y * 7.0 - t * 1.3) * 0.005 * CH * (AMB * 0.6 + mot * 1.5 + hitE * 0.8);
	float bj = (h21(vec2(floor(uv.y * RS.y * 0.5), floor(t * 30.0))) - 0.5) * 0.08 * bandT;
	float vt = floor(t / 3.0);
	float vph = fract(t / 3.0) * 3.0;
	float vslip = step(0.62, h21(vec2(vt, 4.4))) * (h21(vec2(vt, 9.1)) - 0.5) * 0.08 * exp(-vph * 4.0) * CH * (0.5 + drive);
	vec2 tuv = uv + vec2(tear + il + wob + bj, vslip);

	// ---- time slicing + buffer stutter: how old the figure is at this row
	float ts = uI.x * 26.0 * (1.0 - uv.y) * (0.65 + 0.35 * sin(t * 0.3 + uv.y * 2.0));
	ts += uI.x * 8.0 * step(0.7, h21(vec2(floor(uv.y * 18.0), floor(t * 2.0))));            // some bands lag further
	float st = 0.0;
	if (uI.y > 0.5) {
		float L = max(uI.w, 2.0);
		float since = uJ.x - uI.z;
		st = since + L - mod(since, L);   // replay the L frames before the hit in a loop: the age of the looped frame
	}
	float age = ts + st;
	vec2 s0 = silAt(tuv, age);
	vec2 px = vec2(0.006, 0.006 * asp);
	vec2 g = vec2(silAt(tuv + vec2(px.x, 0.0), age).r - silAt(tuv - vec2(px.x, 0.0), age).r,
	              silAt(tuv + vec2(0.0, px.y), age).r - silAt(tuv - vec2(0.0, px.y), age).r);
	float edge = clamp(length(g) * 2.0, 0.0, 1.0);

	// ---- backlit haze, flowing round the body
	vec2 fuv = vec2(uv.x + (wob + bj) * 0.6, uv.y + vslip * 0.5) - g * 0.05 * uD.z + vec2(-g.y, g.x) * 0.06 * uD.z * (fbm(uv * 3.0 + vec2(t * 0.15, -t * 0.1)) - 0.5) * 2.0;
	vec2 Lp = uC.xy + 0.03 * vec2(sin(t * 0.05), cos(t * 0.037));
	float r = length((uv - Lp) * vec2(asp, 1.0));
	float size = max(uB.w, 0.02);
	float hz = clamp(uB.z * (0.55 + 0.9 * uB.x), 0.0, 2.5);
	float f1 = fbm(fuv * vec2(2.0 * asp, 2.0) + vec2(t * 0.01, -t * 0.022));
	float f2 = fbm(fuv * vec2(4.5 * asp, 4.5) + vec2(-t * 0.018, -t * 0.04) + f1 * 1.5);
	float fog = clamp(0.25 + 0.75 * (f1 * 0.65 + f2 * 0.35), 0.0, 1.0);
	float core = exp(-r * r / (size * size * 0.06)) * (1.0 - 0.55 * min(hz, 1.0));
	float light = min(core * 0.7 + exp(-r / size) * 0.22 + exp(-r / (size * 2.2)) * fog * hz * 0.36, 0.8) * (0.8 + 0.2 * uB.y) * uD.w;
	vec3 col = vec3(light) + vec3(0.02) * fog * hz;

	// ---- analog noise: grain mixed with line noise, new every frame
	float fr = floor(t * 30.0);
	float grain = h21(floor(uv * RS * 0.5) + fr * vec2(17.3, 9.1));
	float lines = h21(vec2(floor(uv.y * RS.y * 0.5), fr * 1.7));
	float stat = mix(grain, lines, 0.55);

	// ---- ghosts: older bodies drifting behind it (up and aside), textured by the noise
	float ghost = (silAt(tuv + vec2(0.006, 0.004), 6.0).r * 0.5 + silAt(tuv + vec2(0.014, 0.010), 15.0).r * 0.34
	             + silAt(tuv + vec2(0.024, 0.018), 30.0).r * 0.22) * GH;
	ghost *= (1.0 - clamp(s0.r, 0.0, 1.0)) * (0.55 + 0.45 * stat);
	col *= 1.0 - 0.6 * clamp(ghost, 0.0, 1.0);

	// ---- the traces where it moved break up into noise and dissolve; snow where it moved
	float tr = clamp(s0.g - s0.r, 0.0, 1.0);
	float dis = smoothstep(stat * 0.85, stat * 0.85 + 0.22, tr);
	col *= 1.0 - NOI * dis * (0.35 + 0.45 * stat) * uA.z;
	float snowAmt = clamp(uF.w * (0.1 * mot + moved * 0.7 + 0.4 * hitE * (moved + clamp(s0.r, 0.0, 1.0) * 0.3) + 0.4 * AMB * CH) + bandT * 1.2, 0.0, 1.0);
	col = mix(col, vec3(grain * (0.25 + 0.6 * light) + 0.03), snowAmt * 0.7);
	float lnr = floor(uv.y * RS.y);
	float x0 = h21(vec2(lnr, fr + 11.0)), dlen = 0.05 + 0.25 * h21(vec2(lnr, fr + 5.0));
	float drop = step(1.0 - 0.01 * CH * (AMB * 0.6 + mot * 3.0 + hitE + bandT * 4.0), h21(vec2(lnr, fr * 3.7))) * step(x0, uv.x) * step(uv.x, x0 + dlen);
	col = mix(col, vec3(0.5 * (0.35 + light)), drop * 0.7);

	// ---- the figure, faint features inside it, its lit outline
	float body = clamp(s0.r, 0.0, 1.0) * uA.y;
	col = mix(col, col * 0.03 + vec3(0.012) * stat * NOI, body);
	float rl = relief(tuv);
	col += vec3(1.0) * body * uF.x * (max(rl, 0.0) * 2.2 * (0.35 + light) + 0.02 * smoothstep(0.0, 0.4, light));
	col *= 1.0 - body * uF.x * clamp(-rl * 2.0, 0.0, 0.6);
	col += vec3(0.6) * edge * light * uC.w * (1.0 - body) * uA.y * (0.75 + 0.25 * stat);

	// ---- scan-line displacement: the figure as horizontal lines lifted by the camera picture
	if (uH.x > 0.001) {
		float Lpx = max(uH.z, 2.0);
		float yp = uv.y * RS.y;
		float Dpx = 0.08 * RS.y * uH.y;
		float lsum = 0.0;
		for (int m = 0; m < 28; m++) {
			float yk = (floor(yp / Lpx) - float(m)) * Lpx;
			if (yp - yk > Dpx + Lpx) break;
			vec2 kuv = vec2(tuv.x, (yk + 0.5 * Lpx) / RS.y);
			vec3 c = cam(kuv);
			if (c.z <= 0.0) continue;
			float b = silAt(kuv, age).r * c.z;
			if (b < 0.05) continue;
			float lum = luma(texture(sTD2DInputs[1], c.xy).rgb);
			float yd = yk + 0.5 * Lpx + lum * Dpx * b;
			lsum = max(lsum, (1.0 - smoothstep(0.35, 1.2, abs(yp - yd))) * b * (0.35 + 0.65 * lum));
		}
		col = mix(col, vec3(0.62) * (0.45 + light), clamp(lsum, 0.0, 1.0) * uH.x);
	}

	// ---- tracking overlay: the body as if scanned - more of it when it moves and on hits
	if (uK.x > 0.001) {
		float tv = tracking(tuv, RS, t, max(uK.y, 16.0));
		float tamt = uK.x * (0.4 + 0.6 * max(max(mot, hitE), clamp(moved * 2.0, 0.0, 1.0)));
		col = mix(col, vec3(0.85) * (0.6 + 0.4 * stat), clamp(tv * tamt, 0.0, 1.0));
	}

	// ---- faint scanlines over everything, the edges of the frame sink into darkness
	col *= 1.0 - uE.w * 0.12 * (0.5 + 0.5 * sin(uv.y * RS.y * 3.14159));
	col *= mix(1.0, smoothstep(0.75, 0.3, length(uv - 0.5)), 0.6);
	fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
