// holo_place - puts the head into the square frame (cooks once). input 0 = artist_photo.jpg, input 1 = head_mask.png
// out: r = head mask, g = photo luma (both placed like the video: the head fills 84 % of the height, its left side on
// the frame's left edge, where the photo is cut)
out vec4 fragColor;
const float AX = 0.864458, AY = 0.891685, BY = 0.017664;   // frame -> photo (from the mask's bounding box)
void main() {
	vec2 uv = vUV.st;
	vec2 pimg = vec2(uv.x * AX, (1.0 - uv.y) * AY - BY);      // photo position, image rows (y down)
	if (pimg.x < 0.0 || pimg.y < 0.0 || pimg.x > 1.0 || pimg.y > 1.0) { fragColor = TDOutputSwizzle(vec4(0.0, 0.0, 0.0, 1.0)); return; }
	vec2 puv = vec2(pimg.x, 1.0 - pimg.y);
	float m = texture(sTD2DInputs[1], puv).r;
	float l = dot(texture(sTD2DInputs[0], puv).rgb, vec3(0.299, 0.587, 0.114));
	fragColor = TDOutputSwizzle(vec4(m, l, 0.0, 1.0));
}
