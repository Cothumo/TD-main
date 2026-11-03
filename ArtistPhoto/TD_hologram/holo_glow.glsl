// holo_glow - how bright a particle is at each place, this frame (half resolution). input 0 = holo_maps.
// The head as Screen 2 draws its figure: a dark form in the light with a soft outline catching the light, wobbling as
// the haze flows round it, broken into bright segments travelling along it, rows tearing sideways now and then, two
// faint older outlines trailing behind (right / up); inside only a faint soft relief. All of it only while the face
// is present - it surfaces in soft patches.
// out: r = brightness, g = how much of the face shows here (0..1), b = presence, a = 1
uniform vec4 uG1;   // Streamglow, Figure, Headglow, Rim
uniform vec4 uG2;   // Flow, Tear, Echoes, Detail
out vec4 fragColor;

vec4 maps(vec2 p) { return texture(sTD2DInputs[0], p); }
float rimAt(vec2 p) { float m = maps(p).r; return clamp(4.0 * m * (1.0 - m), 0.0, 1.0); }
float cutAt(vec2 p) {                     // no rim on the cut under the beard (where the neck was removed)
	float ximg = p.x, yimg = 1.0 - p.y;
	return 1.0 - 0.8 * smoothstep(0.62, 0.7, yimg) * (1.0 - smoothstep(0.3, 0.4, ximg));
}

void main() {
	vec2 uv = vUV.st;
	float t = uTime.x, th = loopPhase();
	float hit = hitEnv(t), pres = presence(t);
	float vimg = 1.0 - uv.y;
	// the haze flows round the head: the outline is displaced by a slowly turning noise
	float n1 = fbm(vec2(uv.x, vimg) * 3.2 + 0.45 * vec2(cos(th), sin(th))) - 0.5;
	float n2 = fbm(vec2(uv.x, vimg) * 3.2 + vec2(5.3, 0.0) + 0.45 * vec2(cos(th + 2.1), sin(th + 2.1))) - 0.5;
	vec2 d = vec2(n1, n2) * 2.0 * uG2.x * 18.0 * K720;
	// rows tear sideways now and then (more on hits)
	float row = floor(vimg * 240.0), tk = floor(t * 7.0);
	float band = smoothstep(0.8, 1.0, h21(vec2(row, tk))) + 0.3 * smoothstep(0.6, 1.0, h21(vec2(floor(row / 8.0), tk + 7.0)));
	float tear = (h21(vec2(row, tk + 3.1)) - 0.5) * 0.06 * band * uG2.y * (1.0 + 2.0 * hit);
	vec2 s = vec2(uv.x + d.x + tear, uv.y - d.y - bobUV(t));
	// bright segments travelling along the outline
	float seg = smoothstep(0.35, 0.75, fbm(vec2(uv.x * 7.0 - 0.6 * cos(th), vimg * 7.0 + 0.6 * sin(th) + 9.0)));
	float rim = rimAt(s) * (0.3 + 0.95 * seg);
	// echoes: older outlines trailing behind (right / up)
	rim = max(rim, rimAt(s + vec2(-16.0 * K720 + 0.6 * d.x, -7.0 * K720 + 0.6 * d.y)) * 0.45 * uG2.z * (0.4 + 0.6 * seg));
	rim = max(rim, rimAt(s + vec2(-36.0 * K720 + 0.6 * d.x, -16.0 * K720 + 0.6 * d.y)) * 0.25 * uG2.z * (0.4 + 0.6 * seg));
	rim *= cutAt(s);
	vec4 M = maps(s);
	// the face surfaces in soft patches: a drifting noise decides which parts show first
	float nr = fbm(vec2(uv.x * 2.6 + 0.3 * cos(th + 0.7) + 11.0, vimg * 2.6 + 0.3 * sin(th + 0.7)));
	float rv = clamp((pres * 1.5 - nr + 0.1) / 0.5, 0.0, 1.0) * smoothstep(0.0, 0.6, pres);
	float g = uG1.x * (1.0 - uG1.y * M.g * rv) + (uG1.z * M.g + uG1.w * rim + uG2.w * M.b) * rv;
	fragColor = TDOutputSwizzle(vec4(g, rv, pres, 1.0));
}
