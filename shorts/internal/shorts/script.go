package shorts

// Scene holds one beat of the shorts: a piece of narration plus the visual prompt that goes with it.
// Duration is filled in later after TTS generates the audio and we probe its length.
type Scene struct {
	Index           int
	Narration       string
	ImagePrompt     string
	AudioPath       string
	ImagePath       string
	DurationSeconds float64
}

// stylePrefix is appended to every image prompt to keep the visual look consistent across scenes.
const stylePrefix = "cinematic photorealistic still frame, WWII Eastern Front July 1943, vertical 9:16 composition, anamorphic lens, heavy film grain, dramatic side lighting, IMAX scale epic, hyper detailed, muted desaturated palette with amber and steel blue, no text, no watermark, no logo, no captions"

// KurskScenes is the storyboard for a ~3 minute YouTube Short about the Battle of Kursk.
// Narration is Brazilian Portuguese, written to be spoken by edge-tts pt-BR-AntonioNeural.
func KurskScenes() []Scene {
	raw := []struct {
		narration string
		image     string
	}{
		{
			"Julho de mil novecentos e quarenta e três. Um milhão e meio de soldados. Quase oito mil tanques. A maior batalha blindada da história está prestes a começar.",
			"vast aerial panorama of the Ukrainian steppe at dawn, thousands of tanks in formation stretching to the horizon, low mist, golden first light, distant columns of black smoke",
		},
		{
			"Depois da derrota em Stalingrado, a Alemanha precisava de uma vitória esmagadora. Hitler aposta tudo em uma única ofensiva. O alvo: a cidade de Kursk.",
			"Adolf Hitler studying a huge wall map of the Eastern Front in a dim Wolf's Lair bunker, generals standing in shadow, single overhead spotlight illuminating the map, tense atmosphere",
		},
		{
			"O front formava um saliente de duzentos quilômetros adentrado nas linhas alemãs. O plano era simples: cercar pelos dois lados e destruir o Exército Vermelho.",
			"close up of a 1943 military situation map showing the Kursk salient bulging into German lines, red Soviet markers, grey German arrows converging from north and south, paper texture, hand drawn pencil annotations",
		},
		{
			"A operação foi batizada de Cidadela. Foi adiada quatro vezes, esperando os novos tanques pesados. Cada semana de atraso deu mais tempo para os soviéticos se prepararem.",
			"German Tiger tank emerging from camouflage netting inside a pine forest staging area, mechanics in oily overalls working on the turret, summer light filtering through trees, dust in the air",
		},
		{
			"Tigres de cinquenta e sete toneladas. Panthers recém-saídos da fábrica. Caça-tanques Ferdinand. A elite blindada alemã, reunida em um único setor.",
			"low angle hero shot of a long row of German Tiger one tanks parked in an open field, massive 88 millimeter guns aligned, crewmen loading ammunition, late afternoon sun glinting off steel",
		},
		{
			"Do outro lado, o marechal Júkov tinha informações da inteligência britânica. Sabia o dia, a hora, o ponto exato do ataque. Em três meses, cavou oito linhas defensivas e plantou um milhão de minas.",
			"hundreds of Soviet soldiers and civilians digging deep anti tank trenches across an endless landscape at dusk, lanterns flickering, faces streaked with dirt, exhaustion, biblical scale",
		},
		{
			"Cinco de julho de mil novecentos e quarenta e três. Antes do amanhecer, a artilharia soviética abre fogo primeiro. Os alemães atacam mesmo assim.",
			"hundreds of Soviet howitzers firing in unison before dawn, muzzle flashes lighting the horizon red, silhouettes of artillery crews, thick gun smoke drifting low across the field",
		},
		{
			"Cada quilômetro custava sangue. Os Tigres eram quase invencíveis de frente, mas as minas paravam tudo. Em uma semana, os alemães avançaram apenas trinta quilômetros.",
			"German Tiger tank with broken track immobilized on a minefield, billowing smoke, German infantry sprinting for cover beside it, distant explosions, burning wreckage in background",
		},
		{
			"Doze de julho. Campos de Prokhorovka. Oitocentos tanques colidem em campo aberto. Os T trinta e quatro soviéticos fecham distância. Combate corpo a corpo de blindados.",
			"massive tank brawl in an open wheat field, Soviet T-34 tanks and German Tigers at point blank range, dust clouds choking the sky, sun obscured to a red disc, chaos and motion blur",
		},
		{
			"Fumaça preta cobria o sol. Tanques em chamas, tripulações queimadas vivas. Em poucas horas, centenas de blindados destruídos. Nenhum dos lados conseguiu avançar.",
			"close up of a burning tank with a crew silhouette climbing out, thick oily black smoke blotting out the sun, embers swirling, apocalyptic battlefield stretching behind, orange glow",
		},
		{
			"No norte, os soviéticos lançam sua própria ofensiva. A Alemanha precisa retirar divisões. Hitler cancela Cidadela. A iniciativa muda de mãos para sempre.",
			"Soviet infantry counter attacking through thick smoke behind a wedge of T-34 tanks rolling forward, red banners, determined faces, low sun behind them casting long shadows",
		},
		{
			"Os alemães perderam quase mil tanques. Duzentos mil soldados, mortos ou feridos. Reservas que jamais seriam reconstituídas.",
			"aftermath shot of hundreds of destroyed German tanks scattered across an endless field, crows circling, twisted metal, no living figures, oppressive desolation, grey overcast sky",
		},
		{
			"Kursk foi a última grande ofensiva alemã no front leste. Dali em diante, foram dois anos de recuo lento, até as ruínas de Berlim.",
			"exhausted column of German soldiers retreating through a burning Ukrainian village at twilight, broken vehicles, civilians watching from shadows, distant flashes on the horizon",
		},
		{
			"Stalingrado quebrou o mito da invencibilidade alemã. Kursk quebrou sua máquina de guerra. O fim do Terceiro Reich começou aqui, nos campos de trigo da Ucrânia.",
			"symbolic wide shot of a tattered Soviet red flag planted on top of a destroyed German Panther tank in a wheat field at sunset, wind moving the wheat, golden hour, somber yet triumphant",
		},
	}

	scenes := make([]Scene, len(raw))
	for i, r := range raw {
		scenes[i] = Scene{
			Index:       i,
			Narration:   r.narration,
			ImagePrompt: r.image + ", " + stylePrefix,
		}
	}
	return scenes
}
