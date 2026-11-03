// Ambient Ink - particle billboards (GLSL MAT vertex shader). One instance per particle, positions from sState.
// Each sprite deposits "ink" (r = amount, g = amount x age, b = spray ink) into a float buffer; ink_post.glsl turns
// that into dark ink on paper plus the accent-coloured spray. Old ink spreads (bigger sprites) and pales while keeping its total amount, like ink dissolving.
uniform sampler2D sState;
uniform vec4 uA;   // level, low, mid, high
uniform vec4 uB;   // onset, bright, arc, build
uniform vec4 uR;   // Particlesize (px at 720), output height (px), Dof, Ink
uniform vec4 uS;   // Reactivity, Dilution, Spreadgrowth, Dust
uniform vec4 uU;   // Quality, aspect (W/H), Lifetime, Jet
uniform vec4 uV;   // Sprayamount, Shimmer, phase, hat

out Vertex {
	vec4 col;
	vec2 q;
} oVert;

const float DUSTF = 0.96;         // must match ink_sim.glsl
const float SPRAYF = 0.78;
const float BASEF = 0.50;
const float CAMZ = 3.2;           // camera distance; the z = 0 plane spans y = -1..1

uvec4 pcg4d(uvec4 v)
{
	v = v * 1664525u + 1013904223u;
	v.x += v.y * v.w; v.y += v.z * v.x; v.z += v.x * v.y; v.w += v.y * v.z;
	v ^= v >> 16u;
	v.x += v.y * v.w; v.y += v.z * v.x; v.z += v.x * v.y; v.w += v.y * v.z;
	return v;
}
vec4 rnd4(uint id, uint salt) { return vec4(pcg4d(uvec4(id, salt, id ^ 0x9E3779B9u, salt * 7u + 1u))) * (1.0 / 4294967295.0); }

void main()
{
	int id = TDInstanceID();
	ivec2 rs = textureSize(sState, 0);
	vec4 st = texelFetch(sState, ivec2(id % rs.x, id / rs.x), 0);
	vec4 h = rnd4(uint(id), 11u);
	vec4 h2 = rnd4(uint(id), 23u);
	vec4 g = rnd4(uint(id), 5u);
	bool dust = h.w > DUSTF;
	bool spr = !dust && h.w > SPRAYF;
	bool base = !dust && !spr && h.w > BASEF;
	bool jet = base && h2.w < uU.w;                                  // must match ink_sim.glsl
	float lifetime = (spr ? mix(1.8, 4.0, h2.z) : jet ? mix(6.0, 13.0, h2.z) : base ? mix(5.0, 11.0, h2.z) : mix(8.0, 16.0, h2.z)) * uU.z;

	float life = st.w < 0.0 ? 0.0 : fract(st.w);

	float ageF = dust ? 0.0 : 1.0 - life;
	float d = CAMZ - st.z;
	bool visible = dust ? (g.x < uS.w * 0.025) : (life > 0.0);

	if (!visible || d < 0.4) {
		gl_Position = vec4(2.0, 2.0, 2.0, 1.0);     // outside the clip volume
		oVert.col = vec4(0.0);
		oVert.q = vec2(0.0);
		return;
	}

	float persp = CAMZ / d;
	vec2 ndc = vec2(st.x / uU.y, st.y) * persp;
	float scale = min(uR.y, uR.y * uU.y) / 720.0;                      // sizes follow the frame's short side
	vec4 fz = rnd4(uint(id), uint(uV.z * 3001.0) + 41u);             // changes every frame
	float high = uA.w;
	if (spr || dust)                                                  // treble shimmer (drawn only, not simulated)
		ndc += (fz.xy - 0.5) * 2.0 * vec2(1.0 / uU.y, 1.0) * (1.5 / uR.y) * uV.y * (0.3 + 1.5 * high + 2.0 * uV.w);

	float size0 = uR.x * scale * (0.6 + 0.8 * g.y) * persp;
	float sizePx, amount;
	if (dust) {
		sizePx = uR.x * scale * (0.4 + 0.8 * g.y * g.y) * persp;
		amount = (1.2 + 1.6 * g.z) * (1.0 + uV.y * uS.x * (high + uV.w) * (fz.z - 0.4));   // specks flicker with the treble
		size0 = sizePx;
	} else if (spr) {
		sizePx = uR.x * scale * (0.35 + 0.35 * g.y) * persp;           // fine droplets
		size0 = sizePx;
		amount = uV.x * 1.3 * (0.5 + 0.5 * g.z) * pow(max(1.0 - ageF, 0.0), 1.6) * smoothstep(0.0, 0.06, ageF);
	} else {
		sizePx = size0 * (1.0 + 3.0 * uS.z * ageF);   // dissolving ink spreads out ...
		float fadeIn = smoothstep(0.0, jet ? 0.02 : 0.06, ageF);   // welling / puff ink darkens in gently
		amount = uR.w * (0.4 + 0.6 * g.z) * pow(max(1.0 - ageF, 0.0), uS.y) * fadeIn;   // ... and pales
		amount *= 1.0 + 0.25 * uS.x * (uA.x - 0.5) + 0.35 * uS.x * uA.y;   // breathes with the music, heavier on bass
	}
	float coc = uR.z * scale * abs(d - CAMZ) * 7.0;
	float rad = max(sqrt(sizePx * sizePx + coc * coc), 1.0);
	amount *= (size0 * size0 + 0.5) / (rad * rad + 0.5);            // spreading keeps the total amount of ink
	amount /= max(uU.x, 0.05);                                       // fewer instances drawn -> same density

	vec2 corner = P.xy * 2.0;                                        // Rectangle SOP 1x1 -> -1..1
	vec2 px2ndc = vec2(2.0 / (uR.y * uU.y), 2.0 / uR.y);
	gl_Position = vec4(ndc + corner * rad * px2ndc, 0.5, 1.0);
	oVert.col = spr ? vec4(0.0, 0.0, amount, 1.0) : vec4(amount, amount * ageF, 0.0, 1.0);
	oVert.q = corner;
}
