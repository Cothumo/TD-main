// holo_maps - the head's static maps (cooks once). inputs: 0 = mask, slightly soft; 1 = mask blurred (volume);
// 2 = photo luma, small blur; 3 = photo luma, large blur; 4 = mask, very blurred (where the stream slows down);
// 5 = mask, wide blur (deep inside the head)
// out: r = soft mask (its 0.5 line is the outline), g = volume, b = soft relief (Screen 2 'Detail': only the
// photo's highlights, no traced features), a = slow-down map
out vec4 fragColor;
void main() {
	vec2 uv = vUV.st;
	float m = texture(sTD2DInputs[0], uv).r;
	float vol = texture(sTD2DInputs[1], uv).r;
	float rs = texture(sTD2DInputs[2], uv).g, rl = texture(sTD2DInputs[3], uv).g;
	float deep = smoothstep(0.6, 0.95, texture(sTD2DInputs[5], uv).r);
	float rel = clamp(max(rs - rl, 0.0) * deep / 0.101, 0.0, 1.0);
	float slow = texture(sTD2DInputs[4], uv).r;
	fragColor = TDOutputSwizzle(vec4(m, vol, rel, slow));
}
