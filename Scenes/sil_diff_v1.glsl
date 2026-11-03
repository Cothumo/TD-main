// silhouette: how much each camera pixel belongs to the performer (before blur and threshold).
// input 0 = camera, input 1 = learned background.  mode 0: different from the background, 1: dark (lit from behind)
uniform vec4 uM;   // mode, -, -, -
out vec4 fragColor;
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
void main() {
	vec3 cam = texture(sTD2DInputs[0], vUV.st).rgb;
	vec3 bg = texture(sTD2DInputs[1], vUV.st).rgb;
	float v = uM.x < 0.5 ? length(cam - bg) * 0.75 + abs(luma(cam) - luma(bg)) * 0.5 : 1.0 - luma(cam);
	fragColor = TDOutputSwizzle(vec4(v, v, v, 1.0));
}
