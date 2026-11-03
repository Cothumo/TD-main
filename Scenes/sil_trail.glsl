// silhouette: the body (r) from the blurred difference, and its fading echoes (g).
// input 0 = blurred difference, input 1 = previous output
uniform vec4 uT;   // threshold, softness, echo decay per frame, Silhouette on (0/1)
out vec4 fragColor;
void main() {
	vec2 uv = vUV.st;
	float d = texture(sTD2DInputs[0], uv).r;
	float m = smoothstep(uT.x, uT.x + max(uT.y, 0.001), d) * uT.w;
	vec2 o = uTD2DInfos[1].res.xy * 1.5;
	float pg = (texture(sTD2DInputs[1], uv).g * 2.0 + texture(sTD2DInputs[1], uv + vec2(o.x, 0.0)).g + texture(sTD2DInputs[1], uv - vec2(o.x, 0.0)).g
	          + texture(sTD2DInputs[1], uv + vec2(0.0, o.y)).g + texture(sTD2DInputs[1], uv - vec2(0.0, o.y)).g) / 6.0;   // echoes soften as they fade
	float tr = max(m, pg * uT.z);
	fragColor = TDOutputSwizzle(vec4(m, tr, 0.0, 1.0));
}
