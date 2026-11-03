// NIN Stage - act 2 MELT: video feedback. The picture leaves trails that slowly sink, smear and swirl apart, warped
// by a drifting noise field, like a projection melting. Trails keep the picture's tones: in the dark (negative)
// picture they are light trails, on white paper they are ink trails - so nothing ever brightens into a flash.
// input 0 = the picture, input 1 = the previous output of this TOP (Feedback TOP).
uniform vec4 uM;   // Melt (0..1), time (s), level (smoothed), hit envelope
out vec4 fragColor;
float h21(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y);
}
float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 4; i++) { s += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; } return s / 0.9375; }
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
void main() {
	vec2 uv = vUV.st;
	float melt = clamp(uM.x, 0.0, 1.0), t = uM.y, lvl = uM.z, env = uM.w;
	vec3 src = texture(sTD2DInputs[0], uv).rgb;
	if (melt < 0.001) { fragColor = TDOutputSwizzle(vec4(src, 1.0)); return; }
	// where the trail comes from: a little higher (it sinks), pulled apart by a slow noise field, gently swirling
	vec2 n = vec2(fbm(uv * vec2(3.0, 2.0) + vec2(0.0, t * 0.12)), fbm(uv * vec2(3.0, 2.0) + vec2(7.3, t * 0.1))) - 0.5;
	vec2 c = uv - 0.5;
	float a = 0.0025 * sin(t * 0.07);
	c = mat2(cos(a), -sin(a), sin(a), cos(a)) * c * (1.0 - 0.0015 * (1.0 + env));
	vec2 q = c + 0.5 + vec2(0.0, 0.0028 + 0.002 * lvl) + n * 0.006 * (0.6 + lvl + env);
	vec3 fb = texture(sTD2DInputs[1], clamp(q, vec2(0.001), vec2(0.999))).rgb;
	float paper = smoothstep(0.35, 0.75, luma(texture(sTD2DInputs[0], vec2(0.5), 6.0).rgb * 0.5 + texture(sTD2DInputs[0], vec2(0.25, 0.7)).rgb * 0.25 + texture(sTD2DInputs[0], vec2(0.75, 0.3)).rgb * 0.25));
	float keep = melt * (0.90 + 0.06 * lvl);                    // how long the trails last
	vec3 trailD = max(src, fb * keep);                           // dark picture: light trails
	vec3 trailP = min(src, 1.0 - (1.0 - fb) * keep);             // white paper: ink trails
	fragColor = TDOutputSwizzle(vec4(mix(trailD, trailP, paper), 1.0));
}
