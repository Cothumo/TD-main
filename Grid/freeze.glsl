// freeze: while a pad is held the picture stops and slowly sinks into darkness; released, it melts back to live.
// input 0 = live picture, input 1 = previous output
uniform vec4 uF;   // freeze amount (0..1, smoothed), decay per frame, -, -
out vec4 fragColor;
void main() {
	vec3 live = texture(sTD2DInputs[0], vUV.st).rgb;
	vec3 held = texture(sTD2DInputs[1], vUV.st).rgb * uF.y;
	fragColor = TDOutputSwizzle(vec4(mix(live, held, clamp(uF.x, 0.0, 1.0)), 1.0));
}
