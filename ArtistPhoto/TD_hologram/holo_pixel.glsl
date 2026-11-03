// holo_pixel - soft particle sprite (GLSL MAT pixel shader, additive blending into a float buffer, no depth test)
in Vertex {
	vec4 col;
	vec2 q;
} iVert;

layout(location = 0) out vec4 oFragColor;

void main() {
	float r2 = dot(iVert.q, iVert.q);
	if (r2 > 1.0)
		discard;
	float a = max(exp(-3.5 * r2) - 0.0302, 0.0);
	oFragColor = TDOutputSwizzle(vec4(iVert.col.rgb * a, a));
}
