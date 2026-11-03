// holo_post - the hologram. inputs: 0 = the particles' light (render), 1 = small blur of it, 2 = large blur of it.
// Ambient Ink vibration (ink_post.glsl: per-frame jitter + fast oscillation + row wobble + a trailing second image),
// bloom, projection scanlines, a bright scan band rolling up twice per loop, flicker, horizontal slices glitching
// sideways (more on hits), RGB split, a cool tint, tone-mapped over the dim Screen 2 haze, grain, vignette.
uniform vec4 uP1;   // Gain, Bloom, Scanlines, Scanband
uniform vec4 uP2;   // Flicker, Slices, Chroma (px at 720), Vibration
uniform vec4 uP3;   // Tint r, g, b, Backlight
out vec4 fragColor;

float lightAt(vec2 q) {
	return texture(sTD2DInputs[0], q).r + uP1.y * (0.55 * texture(sTD2DInputs[1], q).r + 0.35 * texture(sTD2DInputs[2], q).r);
}

void main() {
	vec2 uv = vUV.st;
	vec2 RS = uTDOutputInfo.res.zw;
	float Kp = RS.y / 720.0;
	float t = uTime.x, th = loopPhase(), frame = uBur.z;
	float hit = hitEnv(t);
	float yimg = (1.0 - uv.y) * RS.y;

	// slices: horizontal bands jump sideways for a frame or two
	float blk = floor(yimg / (14.0 * Kp));
	vec4 r = rnd4(uint(blk) + 7u, uint(floor(frame / 2.0)) * 13u + 3u);
	float sl = r.x < (0.05 + 0.3 * hit) * uP2.y ? (r.y - 0.5) * 2.0 * 10.0 * Kp * (1.0 + 2.0 * hit) : 0.0;

	// vibration (ink_post.glsl)
	float ve = uEnv.w >= 0.0 ? clamp(uEnv.w, 0.0, 1.0) : burstEnv(t, 0.55);
	float vib = clamp((0.12 + 0.6 * ve + 0.05 * (h21(vec2(frame, 3.3)) - 0.5)) * uP2.w, 0.0, 3.0);
	vec2 j = vec2(h21(vec2(frame, 1.37)), h21(vec2(frame, 7.91))) * 2.0 - 1.0;
	vec2 off = (j * 0.65 + vec2(sin(frame * 2.71), cos(frame * 3.37)) * 0.35) * vib * 16.0 * Kp;
	off.x += sin(yimg * (0.045 / Kp) + frame * 1.9) * vib * 5.0 * Kp;
	vec2 o = vec2(off.x, -off.y) / RS;
	float gw = min(0.45 * vib, 0.6);

	// RGB split (more on hits)
	float ca = uP2.z * Kp / 1.5 * (1.0 + 3.0 * hit);
	vec2 q = uv - vec2(sl / RS.x, 0.0);
	vec3 c;
	for (int k = 0; k < 3; k++) {
		vec2 qk = q + vec2((float(k) - 1.0) * ca / RS.x, 0.0);
		c[k] = mix(lightAt(qk + o), lightAt(qk - 1.6 * o), gw);
	}

	// projection: scanlines, the scan band rolling up, flicker
	float scan = 1.0 - uP1.z * (0.5 + 0.5 * sin(yimg * TAU / (2.0 * Kp)));
	float by = fract(1.0 - 2.0 * t / uTime.y);
	float d = abs((1.0 - uv.y) - by); d = min(d, 1.0 - d);
	float band = uP1.w * (0.9 * exp(-pow(d / 0.035, 2.0)) + 0.6 * exp(-pow(d / 0.004, 2.0)));
	float flick = 1.0 + uP2.x * (h21(vec2(frame, 9.9)) * 2.0 - 1.0) - (h21(vec2(frame, 4.2)) > 0.965 ? 0.25 : 0.0);
	c *= scan * (1.0 + band) * flick;

	// the dim Screen 2 haze and its far light behind
	vec2 ui = vec2(uv.x, 1.0 - uv.y);
	float f1 = fbm(ui * 2.0 + 0.22 * vec2(cos(th), sin(th)) + vec2(0.0, 3.0));
	float f2 = fbm(ui * 4.5 + 0.3 * vec2(cos(-th + 1.0), sin(-th + 1.0)) + f1 * 1.5);
	float fog = clamp(0.25 + 0.75 * (f1 * 0.65 + f2 * 0.35), 0.0, 1.0);
	float rr = length(ui - vec2(0.55 + 0.02 * sin(th), 0.42 + 0.02 * cos(th)));
	float bg = (exp(-rr / 0.4) * 0.22 + exp(-rr / 0.9) * fog * 0.3) * uP3.w + 0.015 * fog;

	float grain = (h21(floor(gl_FragCoord.xy / 2.0) + vec2(frame * 17.3, frame * 9.1)) - 0.5) * 0.035;
	float vig = 1.0 + (smoothstep(0.78, 0.3, length(uv - 0.5)) - 1.0) * 0.55;
	vec3 col = (vec3(bg) + uP3.rgb * (1.0 - exp(-c * uP1.x)) + grain) * vig;
	fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
