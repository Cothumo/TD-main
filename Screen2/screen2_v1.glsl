// Screen 2 - the live silhouette on its own screen: the performer as a dark figure against one soft light far behind
// drifting haze; the haze flows round the body, faint echoes trail its movement, its outline catches the light.
// The pads (Stems) thicken the haze, the music's level breathes the light. Grey only, nothing flashes.
// input 0 = silhouette from /project1/scenes/sil (r = body, g = trail; camera picture coordinates)
uniform vec4 uA;   // time (s), Figure (0..1), Echoes (0..1), Mirror (0/1)
uniform vec4 uB;   // pads (0..1), level (0..1), Haze, Lightsize
uniform vec4 uC;   // light x, light y, Scale, Rim
uniform vec4 uD;   // X, Y (figure offset), Flow, Light (brightness)
out vec4 fragColor;
float h21(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y);
}
float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; } return s / 0.96875; }

vec2 sil(vec2 uv) {
	vec2 r0 = uTD2DInfos[0].res.zw;
	float Ac = r0.x / max(r0.y, 1.0);
	float Ao = uTDOutputInfo.res.z / uTDOutputInfo.res.w;
	vec2 c = uv - 0.5 - uD.xy;
	c /= max(uC.z, 0.05);
	c.x *= Ao / max(Ac, 0.01);
	c += 0.5;
	if (uA.w > 0.5) c.x = 1.0 - c.x;
	if (c.x < 0.0 || c.y < 0.0 || c.x > 1.0 || c.y > 1.0) return vec2(0.0);
	vec2 e = smoothstep(0.0, 0.04, c) * smoothstep(0.0, 0.04, 1.0 - c);
	return texture(sTD2DInputs[0], c).rg * e.x * e.y;
}

void main() {
	vec2 uv = vUV.st;
	float t = uA.x;
	vec2 RS = uTDOutputInfo.res.zw;
	float asp = RS.x / RS.y;
	vec2 s0 = sil(uv);
	vec2 px = vec2(0.006, 0.006 * asp);
	vec2 g = vec2(sil(uv + vec2(px.x, 0.0)).r - sil(uv - vec2(px.x, 0.0)).r, sil(uv + vec2(0.0, px.y)).r - sil(uv - vec2(0.0, px.y)).r);
	float edge = clamp(length(g) * 2.0, 0.0, 1.0);

	// the haze flows round the body
	vec2 fuv = uv - g * 0.05 * uD.z + vec2(-g.y, g.x) * 0.06 * uD.z * (fbm(uv * 3.0 + vec2(t * 0.15, -t * 0.1)) - 0.5) * 2.0;
	vec2 L = uC.xy + 0.03 * vec2(sin(t * 0.05), cos(t * 0.037));
	vec2 dl = (uv - L) * vec2(asp, 1.0);
	float r = length(dl);
	float size = max(uB.w, 0.02);
	float hz = clamp(uB.z * (0.55 + 0.9 * uB.x), 0.0, 2.5);
	float f1 = fbm(fuv * vec2(2.0 * asp, 2.0) + vec2(t * 0.01, -t * 0.022));
	float f2 = fbm(fuv * vec2(4.5 * asp, 4.5) + vec2(-t * 0.018, -t * 0.04) + f1 * 1.5);
	float fog = clamp(0.25 + 0.75 * (f1 * 0.65 + f2 * 0.35), 0.0, 1.0);
	float core = exp(-r * r / (size * size * 0.06)) * (1.0 - 0.55 * min(hz, 1.0));
	float glow = exp(-r / size);
	float scatter = exp(-r / (size * 2.2)) * fog * hz;
	float light = min(core * 0.7 + glow * 0.22 + scatter * 0.36, 0.8) * (0.8 + 0.2 * uB.y) * uD.w;
	vec3 col = vec3(light) + vec3(0.02) * fog * hz;
	// the figure, its echoes, its lit outline
	float body = clamp(s0.r, 0.0, 1.0) * uA.y;
	float tr = clamp(s0.g - s0.r, 0.0, 1.0) * uA.z;
	col *= 1.0 - 0.45 * tr;
	col = mix(col, col * 0.03, body);
	col += vec3(0.6) * edge * light * uC.w * (1.0 - body) * uA.y;
	// the frame's edges sink into darkness
	vec2 v = (uv - 0.5) * vec2(1.0, 1.0);
	col *= mix(1.0, smoothstep(0.75, 0.3, length(v)), 0.6);
	fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
