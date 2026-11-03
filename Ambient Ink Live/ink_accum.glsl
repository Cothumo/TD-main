// Ambient Ink - smooth streaks (GLSL TOP). Input 0 = this frame's render, input 1 = last result (accum_fb).
uniform vec4 uK;   // Trails, reset, 0, 0

out vec4 fragColor;

void main()
{
	vec4 cur = texture(sTD2DInputs[0], vUV.st);
	vec4 prev = texture(sTD2DInputs[1], vUV.st);
	float keep = uK.y > 0.5 ? 0.0 : clamp(uK.x * (1.0 - 0.4 * uK.z), 0.0, 0.97);
	fragColor = TDOutputSwizzle(mix(cur, prev, keep));
}
