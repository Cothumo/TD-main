// Ambient Ink Live - lays the ink over the picture below it (neith_live), in either of its modes:
// The ink is a range of greys (Inktonelight for thin ink .. Inktone for dense ink), whatever neith_live does - it never
// inverts.
// input 0 = the picture below, input 1 = the ink (ink_track2/OUT: ink on white paper, with all its effects:
// vibration, disruption, sprays, dust), input 2 = unused.
uniform vec4 uL;   // amount (Layeramount x presence), 0, ink tone (Inktone), threshold (Inkthreshold)
uniform vec4 uM;   // 0, ink tone of thin ink (Inktonelight), Inkmatch (0..1), 0
out vec4 fragColor;
void main()
{
	vec2 uv = vUV.st;
	vec3 under = texture(sTD2DInputs[0], uv).rgb;
	vec3 ink = texture(sTD2DInputs[1], uv).rgb;
	// the ink keeps its own range of greys: dense, fresh ink is dark (Inktone), thin and old ink fades to a lighter grey
	// (Inktonelight); faint haze below the threshold is left out, so the picture below stays clean
	float dens = 1.0 - dot(ink, vec3(0.299, 0.587, 0.114));
	float d = smoothstep(uL.w, 0.75, dens) * uL.x;
	float g = smoothstep(uL.w, 0.95, dens);
	vec3 tone = vec3(mix(uM.y, uL.z, g));
	// blend the ink's grey towards a slightly darker shade of what lies beneath it (Inkmatch), so it sinks into the
	// picture instead of sitting on top of it
	vec3 shade = under * mix(0.82, 0.55, g);
	tone = mix(tone, shade, clamp(uM.z, 0.0, 1.0));
	fragColor = TDOutputSwizzle(vec4(mix(under, tone, d), 1.0));
}
