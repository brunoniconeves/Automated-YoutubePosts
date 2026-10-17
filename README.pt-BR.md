# Automated YouTube Posts

*[English](README.md)*

Transforme o progresso do seu projeto em episódios para o YouTube editando o mínimo possível: você fala para o
celular, e o fluxo (com o Claude Code, pela skill incluída) faz o resto.

Para cada episódio ele gera:

- um **roteiro** (`roteiro.html`) escrito a partir dos commits desde o último episódio;
- um **vídeo longo 16:9**: sua abertura em tela cheia, depois você num canto sobre as cenas de cada tópico, e direto
  para a vinheta do canal com música (um trecho final só com música apenas se o roteiro pedir). **Sem legenda na imagem**: ele gera arquivos `.srt` em cada idioma
  para subir no YouTube Studio;
- um **Short 9:16 por idioma** com legenda queimada palavra por palavra (a palavra falada num quadro colorido),
  cortado logo depois da sua última palavra e com fusão para a vinheta com música.

Primeiro saem prévias leves; os finais só depois da sua aprovação.

![Legenda palavra por palavra](docs/short_captions.gif) ![Short em português](docs/short_pt.png) ![Short em inglês](docs/short_en.png)

![Quadro do vídeo longo](docs/long.png)

![Vinheta do canal](docs/sting.png)

## Requisitos

- Python 3.10+, `pip install -r requirements.txt` (faster-whisper, Pillow)
- ffmpeg 6+ com libx264 no PATH (ou `$FFMPEG` / `$FFPROBE`)
- Windows para os padrões incluídos (fontes no `channel.json`, a voz offline do demo); troque os caminhos das
  fontes e o comando de captura para rodar em outro sistema.
- Opcional: [Claude Code](https://claude.com/claude-code); a skill em `.claude/skills/youtube-episode` conduz tudo.

## Resultado de exemplo

O episódio demo, do jeito que o fluxo gerou: [vídeo longo](examples/demo/episode_demo_long.mp4) (16:9, sem legenda
na imagem) com as legendas [pt](examples/demo/episode_demo_long.pt.srt) e [en](examples/demo/episode_demo_long.en.srt),
[Short em português](examples/demo/episode_demo_short_pt.mp4) e [Short em inglês](examples/demo/episode_demo_short_en.mp4).

## Começo rápido: refazer o demo

O demo não precisa de câmera nem de projeto: é uma apresentação narrada do próprio fluxo. Tudo de que ele parte está
no repositório (`brand/`: logo, vinhetas 3D e música; `demo/assets/`: a narração e os slides), então um clone novo
refaz o demo sem Blender, sem voz sintetizada e sem navegador:

```bash
pip install -r requirements.txt
python demo/make_demo.py                   # episodes/demo: takes, cenas, episode.json, translations.json
python tools/transcribe.py episodes/demo/takes/intro.mp4
python tools/transcribe.py episodes/demo/takes/main.mp4
python tools/build_long.py episodes/demo
python tools/build_short.py episodes/demo
python tools/make_subs.py episodes/demo
python tools/captions.py episodes/demo pt
python tools/captions.py episodes/demo en
python tools/finalize.py episodes/demo     # episodes/demo/final: longo + .srt, Short PT, Short EN
python tools/check_sums.py                 # compara com examples/demo (SHA-256)
```

Com as mesmas versões das ferramentas (abaixo), o resultado é idêntico byte a byte: um clone novo deu o mesmo
SHA-256 nos cinco arquivos. Com outra build do ffmpeg/x264, outra versão do faster-whisper ou outra fonte, sai o mesmo
vídeo, mas não os mesmos bytes, e o `check_sums.py` vai dizer DIFFERENT.

Feito com: Windows 11, Python 3.11.6, ffmpeg 7.1.1 (build essentials da gyan.dev), faster-whisper 1.2.1 (ctranslate2
4.8.3, modelo large-v3-turbo, CPU int8), Pillow 12.3.0, numpy 1.26.2; fontes Arial Black e Arial Bold (legendas e
rótulos). `python demo/make_demo.py --regenerate` refaz a narração (voz do Windows "Microsoft Maria Desktop") e os
slides (Edge ou Chrome em modo headless); `python tools/make_brand.py --blender "<blender>"` refaz a marca (Blender
4.2+ para as vinhetas 3D, versão 2D sem ele).

## Seus episódios

1. Edite o `channel.json`: nome do canal, `project_repo` (o código sobre o qual são os episódios), idiomas e
   estilo da legenda. Troque o `brand/` pelo seu logo, vinhetas e música.
2. `python tools/new_episode.py` cria `episodes/<hoje>/` e o `changes.json`. Com o Claude Code, peça um episódio
   e a skill escreve o `roteiro.html`.
3. Grave os takes (`takes/intro.mp4`, `takes/main.mp4`) e as cenas em `broll/`.
4. Transcreva, preencha o `episode.json` (veja `tools/episode.example.json`), monte, traduza
   (`translations.todo.json` -> `translations.json`), veja as prévias e finalize.

Os episódios (seus takes, sua voz e todos os vídeos) ficam fora do git e não saem da sua máquina.

## Licença

MIT
