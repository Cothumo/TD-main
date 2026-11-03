// silhouette background: a slowly learned picture of the empty stage. input 0 = camera, input 1 = the previous background
uniform vec4 uR;   // rate this frame (1 = capture now), -, -, -
out vec4 fragColor;
void main() {
	vec3 cam = texture(sTD2DInputs[0], vUV.st).rgb;
	vec3 bg = texture(sTD2DInputs[1], vUV.st).rgb;
	fragColor = TDOutputSwizzle(vec4(mix(bg, cam, clamp(uR.x, 0.0, 1.0)), 1.0));
}
