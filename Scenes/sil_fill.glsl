// silhouette: close the holes inside the figure (where it looked like the background) without growing its outline.
// input 0 = body / trail, input 1 = the same, widely blurred
out vec4 fragColor;
void main() {
	vec2 uv = vUV.st;
	vec4 a = texture(sTD2DInputs[0], uv);
	float w = texture(sTD2DInputs[1], uv).r;
	float m = max(a.r, smoothstep(0.55, 0.8, w));   // surrounded by body = body; at the outline the blur stays near 0.5
	fragColor = TDOutputSwizzle(vec4(m, max(a.g, m), 0.0, 1.0));
}
