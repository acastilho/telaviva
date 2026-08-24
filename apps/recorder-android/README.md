# TelaViva Recorder (Android)

MVP de gravador de tela para Android feito com **Python/Kivy + PyJNIus**, empacotado com Buildozer/python-for-android.

O caso de uso principal é gravar a tela do ChatGPT com áudio sem depender de captura de áudio interno do outro aplicativo.

## Como funciona

1. O app pede permissão do microfone.
2. O Android mostra o diálogo oficial de `MediaProjection` para autorizar a captura da tela.
3. O app inicia um foreground service `mediaProjection|microphone`.
4. O serviço grava:
   - vídeo da tela via `MediaProjection` + `VirtualDisplay`;
   - áudio via microfone;
   - MP4 H.264 + AAC.
5. O arquivo é publicado em **Filmes/TelaViva** usando `MediaStore`.

## Uso com ChatGPT

Para o cenário que motivou este app:

1. Abra o TelaViva Recorder.
2. Toque em **GRAVAR** e autorize tela + microfone.
3. Quando aparecer `GRAVANDO`, abra o ChatGPT.
4. Use o **chat normal**, não o modo de voz.
5. Na resposta que deseja narrar, use **Ler em voz alta**.
6. O som sai pelo alto-falante e é captado pelo microfone do TelaViva Recorder.
7. Volte ao gravador e toque em **PARAR**.

> O modo de voz do ChatGPT também usa o microfone. Android normalmente não permite que dois apps mantenham o microfone simultaneamente. Por isso este MVP usa o ChatGPT em modo normal + leitura em voz alta.

## Estrutura

```text
recorder-android/
├── main.py
├── buildozer.spec
├── services/
│   └── recorder.py
└── android_src/
    └── com/telaviva/recorder/
        └── ProjectionBridge.java
```

### `main.py`

Interface Kivy, permissões de runtime e solicitação de consentimento do `MediaProjection`.

### `services/recorder.py`

Foreground service Python que mantém a gravação quando outro app está na frente. Recebe o token de autorização, cria o `MediaRecorder`, o `VirtualDisplay` e publica o MP4 no `MediaStore`.

### `ProjectionBridge.java`

Bridge mínimo para duas operações Android difíceis de transportar diretamente via PyJNIus:

- serializar/deserializar o `Intent` de consentimento entre processos;
- implementar `MediaProjection.Callback`, obrigatório em Android 14+ antes de `createVirtualDisplay()`.

## Compilar localmente

Em Linux:

```bash
cd apps/recorder-android
python -m pip install buildozer cython
buildozer -v android debug
```

O APK será criado em `bin/`.

## GitHub Actions

O workflow `.github/workflows/android-recorder-apk.yml` compila automaticamente o APK e publica o arquivo como artifact `telaviva-recorder-apk`.

## Requisitos Android

- Android 10+ (`minapi = 29`)
- arquitetura ARM64
- permissão de microfone
- consentimento de captura de tela a cada nova sessão

## Próximos passos

- botão flutuante para parar sem voltar ao app;
- configuração de resolução/bitrate;
- contador de tempo;
- opção sem microfone;
- teste em Samsung/Android 14+ e ajustes por fabricante;
- APK assinado para distribuição.

<!-- COMPROMISSO-GERAL-A-CASTILHO -->

---

## Compromisso Geral

**Sempre na melhor prática. No caminho do bem maior.**

**Ir até o fim sem sair do caminho, seja ele qual for.**

