// ghosts: three older silhouettes packed into one picture. inputs 0, 1, 2 = the body some frames ago (newest first)
out vec4 fragColor;
void main() {
	vec2 uv = vUV.st;
	fragColor = TDOutputSwizzle(vec4(texture(sTD2DInputs[0], uv).r, texture(sTD2DInputs[1], uv).r, texture(sTD2DInputs[2], uv).r, 1.0));
}
