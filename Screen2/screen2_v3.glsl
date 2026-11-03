// Screen 2 - the live silhouette on its own screen, backlit haze: the performer as a dark figure against one soft
// light far behind drifting haze; the haze flows round the body, the outline catches the light.
// NIN style traces: where the figure moved it leaves traces that break up into analog noise (grain, line noise) and
// dissolve; delayed ghosts of the figure drift behind it; while it moves its rows tear sideways like a bad signal.
// Chaos: a failing analog TV - a tracking band rolls through, the sync wobbles, odd and even lines drift apart,
// snow fills where it moved, thin signal dropouts streak across; more when it moves and on strong hits.
// The pads (Stems) thicken the haze, the music's level breathes the light. Grey only.
// input 0 = silhouette (r = body, g = trail) from /project1/scenes/sil, input 1 = delayed bodies (r, g, b = older),
// input 2 = the camera picture (for the faint features inside the figure)
uniform vec4 uA;   // time (s), Figure (0..1), Echoes (0..1), Mirror (0/1)
uniform vec4 uB;   // pads (0..1), level (0..1), Haze, Lightsize
uniform vec4 uC;   // light x, light y, Scale, Rim
uniform vec4 uD;   // X, Y (figure offset), Flow, Light (brightness)
uniform vec4 uE;   // Noise (traces), Tear, Ghosts, Scanlines
uniform vec4 uF;   // Detail (features inside the figure), -, -, -
uniform vec4 uG;   // Chaos (analog TV), motion (0..1, how much the figure moves), hit envelope, Snow
out vec4 fragColor;
float h21(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y);
}
float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; } return s / 0.96875; }

// frame position -> camera picture position (the camera fills the screen, scaled / moved / mirrored); w = inside
vec3 cam(vec2 uv) {
	vec2 r0 = uTD2DInfos[0].res.zw;
	float Ac = r0.x / max(r0.y, 1.0);
	float Ao = uTDOutputInfo.res.z / uTDOutputInfo.res.w;
	vec2 c = uv - 0.5 - uD.xy;
	c /= max(uC.z, 0.05);
	c.x *= Ao / max(Ac, 0.01);
	c += 0.5;
	if (uA.w > 0.5) c.x = 1.0 - c.x;
	vec2 e = smoothstep(0.0, 0.04, c) * smoothstep(0.0, 0.04, 1.0 - c);
	float inside = (c.x < 0.0 || c.y < 0.0 || c.x > 1.0 || c.y > 1.0) ? 0.0 : e.x * e.y;
	return vec3(c, inside);
}
vec2 sil(vec2 uv) { vec3 c = cam(uv); return c.z > 0.0 ? texture(sTD2DInputs[0], c.xy).rg * c.z : vec2(0.0); }
vec3 old(vec2 uv) { vec3 c = cam(uv); return c.z > 0.0 ? texture(sTD2DInputs[1], c.xy).rgb * c.z : vec3(0.0); }
// the features of the figure: the camera's fine relief (its brightness against its own surroundings)
float relief(vec2 uv) {
	vec3 c = cam(uv);
	if (c.z <= 0.0) return 0.0;
	vec2 o = uTD2DInfos[2].res.xy * 2.5;
	float l = dot(texture(sTD2DInputs[2], c.xy).rgb, vec3(0.299, 0.587, 0.114));
	float m = 0.0;
	m += dot(texture(sTD2DInputs[2], c.xy + vec2(o.x, 0.0)).rgb, vec3(0.333));
	m += dot(texture(sTD2DInputs[2], c.xy - vec2(o.x, 0.0)).rgb, vec3(0.333));
	m += dot(texture(sTD2DInputs[2], c.xy + vec2(0.0, o.y)).rgb, vec3(0.333));
	m += dot(texture(sTD2DInputs[2], c.xy - vec2(0.0, o.y)).rgb, vec3(0.333));
	m += dot(texture(sTD2DInputs[2], c.xy + o * 2.0).rgb, vec3(0.333));
	m += dot(texture(sTD2DInputs[2], c.xy - o * 2.0).rgb, vec3(0.333));
	return (l - m / 6.0) * c.z;
}

void main() {
	vec2 uv = vUV.st;
	float t = uA.x;
	vec2 RS = uTDOutputInfo.res.zw;
	float asp = RS.x / RS.y;
	float NOI = uE.x, TEAR = uE.y, GH = uE.z * uA.z;

	// ---- where it moved: the trail at this point (untorn) decides how much the signal breaks up here
	vec2 s_ = sil(uv);
	float moved = clamp(s_.g - s_.r, 0.0, 1.0);
	// rows tear sideways while it moves (some rows, changing a few times a second - a bad signal, not a strobe)
	float row = floor(uv.y * 240.0);
	float tk = floor(t * 7.0);
	float rn = h21(vec2(row, tk));
	float band = smoothstep(0.78, 1.0, rn) + 0.35 * smoothstep(0.5, 1.0, h21(vec2(floor(uv.y * 30.0), tk + 7.0)));
	float tear = (h21(vec2(row, tk + 3.1)) - 0.5) * 0.05 * TEAR * band * smoothstep(0.02, 0.4, moved + 0.6 * old(uv).r);
	vec2 tuv = uv + vec2(tear, 0.0);
	// ---- analog TV chaos: tracking band, sync wobble, interlace drift (stronger with movement and on hits)
	float CH = uG.x;
	float mot = clamp(uG.y * 6.0, 0.0, 1.0);
	float hitE = clamp(uG.z, 0.0, 1.0);
	float by = fract(-t * 0.045 + 0.3 * sin(t * 0.013));
	float bdy = abs(uv.y - by); bdy = min(bdy, 1.0 - bdy);
	float bandT = (1.0 - smoothstep(0.0, 0.05 + 0.04 * mot, bdy)) * CH * (0.35 + 0.65 * max(mot, hitE));
	float wob = sin(uv.y * 38.0 + t * 3.1) * sin(uv.y * 7.0 - t * 1.3) * 0.006 * CH * (mot * 1.5 + hitE * 0.8);
	float bj = (h21(vec2(floor(uv.y * RS.y * 0.5), floor(t * 30.0))) - 0.5) * 0.08 * bandT;
	float il = (mod(floor(uv.y * RS.y), 2.0) - 0.5) * 0.004 * CH * mot;
	tuv.x += wob + bj + il;

	vec2 s0 = sil(tuv);
	vec2 px = vec2(0.006, 0.006 * asp);
	vec2 g = vec2(sil(tuv + vec2(px.x, 0.0)).r - sil(tuv - vec2(px.x, 0.0)).r, sil(tuv + vec2(0.0, px.y)).r - sil(tuv - vec2(0.0, px.y)).r);
	float edge = clamp(length(g) * 2.0, 0.0, 1.0);

	// ---- backlit haze, flowing round the body
	vec2 fuv = vec2(uv.x + (wob + bj) * 0.6, uv.y) - g * 0.05 * uD.z + vec2(-g.y, g.x) * 0.06 * uD.z * (fbm(uv * 3.0 + vec2(t * 0.15, -t * 0.1)) - 0.5) * 2.0;
	vec2 L = uC.xy + 0.03 * vec2(sin(t * 0.05), cos(t * 0.037));
	vec2 dl = (uv - L) * vec2(asp, 1.0);
	float r = length(dl);
	float size = max(uB.w, 0.02);
	float hz = clamp(uB.z * (0.55 + 0.9 * uB.x), 0.0, 2.5);
	float f1 = fbm(fuv * vec2(2.0 * asp, 2.0) + vec2(t * 0.01, -t * 0.022));
	float f2 = fbm(fuv * vec2(4.5 * asp, 4.5) + vec2(-t * 0.018, -t * 0.04) + f1 * 1.5);
	float fog = clamp(0.25 + 0.75 * (f1 * 0.65 + f2 * 0.35), 0.0, 1.0);
	float core = exp(-r * r / (size * size * 0.06)) * (1.0 - 0.55 * min(hz, 1.0));
	float glow = exp(-r / size);
	float scatter = exp(-r / (size * 2.2)) * fog * hz;
	float light = min(core * 0.7 + glow * 0.22 + scatter * 0.36, 0.8) * (0.8 + 0.2 * uB.y) * uD.w;
	vec3 col = vec3(light) + vec3(0.02) * fog * hz;

	// ---- analog noise: fine grain mixed with line noise (whole rows), new every frame
	float fr = floor(t * 30.0);
	float grain = h21(floor(uv * RS * 0.5) + fr * vec2(17.3, 9.1));
	float lines = h21(vec2(floor(uv.y * RS.y * 0.5), fr * 1.7));
	float stat = mix(grain, lines, 0.55);

	// ---- ghosts: older bodies drifting behind it (up and aside), textured by the noise
	vec3 o3 = old(tuv + vec2(0.006, 0.004));
	vec3 o3b = old(tuv + vec2(0.014, 0.010));
	vec3 o3c = old(tuv + vec2(0.024, 0.018));
	float ghost = (o3.r * 0.5 + o3b.g * 0.34 + o3c.b * 0.22) * GH;
	ghost *= (1.0 - clamp(s0.r, 0.0, 1.0)) * (0.55 + 0.45 * stat);
	col *= 1.0 - 0.6 * clamp(ghost, 0.0, 1.0);

	// ---- the traces where it moved break up into noise and dissolve
	float tr = clamp(s0.g - s0.r, 0.0, 1.0);
	float dis = smoothstep(stat * 0.85, stat * 0.85 + 0.22, tr);          // fading traces crumble into the noise
	col *= 1.0 - NOI * dis * (0.35 + 0.45 * stat) * uA.z;
	col += vec3(0.08) * NOI * dis * smoothstep(0.7, 1.0, lines) * light;   // a faint lit line here and there

	// ---- snow where it moved and in the tracking band; thin dropouts streak across now and then
	float snowAmt = clamp(bandT * 1.2 + uG.w * CH * (0.12 * mot + moved * 0.6 + 0.4 * hitE * (moved + clamp(s0.r, 0.0, 1.0) * 0.3)), 0.0, 1.0);
	col = mix(col, vec3(grain * (0.25 + 0.6 * light) + 0.03), snowAmt * 0.7);
	float lnr = floor(uv.y * RS.y);
	float x0 = h21(vec2(lnr, fr + 11.0)), dlen = 0.05 + 0.25 * h21(vec2(lnr, fr + 5.0));
	float drop = step(1.0 - 0.012 * CH * (mot * 3.0 + hitE + bandT * 4.0), h21(vec2(lnr, fr * 3.7))) * step(x0, uv.x) * step(uv.x, x0 + dlen);
	col = mix(col, vec3(0.5 * (0.35 + light)), drop * 0.7);

	// ---- the figure and its lit outline (the outline breaks up a little in the noise)
	float body = clamp(s0.r, 0.0, 1.0) * uA.y;
	col = mix(col, col * 0.03 + vec3(0.012) * stat * NOI, body);
	// faint features inside the figure: its relief catches a little of the light (eyes, folds, hands)
	float rl = relief(tuv);
	col += vec3(1.0) * body * uF.x * (max(rl, 0.0) * 2.2 * (0.35 + light) + 0.02 * smoothstep(0.0, 0.4, light));
	col *= 1.0 - body * uF.x * clamp(-rl * 2.0, 0.0, 0.6);
	col += vec3(0.6) * edge * light * uC.w * (1.0 - body) * uA.y * (0.75 + 0.25 * stat);

	// ---- faint scanlines over everything, the edges of the frame sink into darkness
	col *= 1.0 - uE.w * 0.12 * (0.5 + 0.5 * sin(uv.y * RS.y * 3.14159));
	col *= mix(1.0, smoothstep(0.75, 0.3, length(uv - 0.5)), 0.6);
	fragColor = TDOutputSwizzle(vec4(clamp(col, 0.0, 1.0), 1.0));
}
