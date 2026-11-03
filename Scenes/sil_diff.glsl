// silhouette: how much each camera pixel belongs to the performer (before blur and threshold).
// input 0 = camera, input 1 = learned background, input 2 = NVIDIA AI person key (alpha: 1 = person)
// mode 0: different from the empty stage, 1: dark figure (lit from behind), 2: AI person detection
uniform vec4 uM;   // mode, -, -, -
out vec4 fragColor;
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
void main() {
	vec3 cam = texture(sTD2DInputs[0], vUV.st).rgb;
	vec3 bg = texture(sTD2DInputs[1], vUV.st).rgb;
	float v;
	if (uM.x > 1.5) v = smoothstep(0.25, 0.75, texture(sTD2DInputs[2], vUV.st).a);   // the NVIDIA key comes in the alpha channel
	else if (uM.x > 0.5) v = 1.0 - luma(cam);
	else v = length(cam - bg) * 0.75 + abs(luma(cam) - luma(bg)) * 0.5;
	fragColor = TDOutputSwizzle(vec4(v, v, v, 1.0));
}
