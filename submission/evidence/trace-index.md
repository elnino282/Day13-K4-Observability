# Trace index

## Baseline — prompt label `baseline`, version 1

1. `f00edc1a5e8a6457936c6e0f5cb31a56`
2. `6c77ffb8bb5dd4cd68fcfdbdc57c0f79`
3. `d6c91f32f40530c706204d12bef3a98a`
4. `13cdb6235e78393a0b47248c92d26f26`
5. `950cee7561d300446320845997e34278`
6. `2f87ceb1d3445dd9f20d821028da6f36`
7. `c861f18668491f8855146e4d61a4b0c1`
8. `19c5bc7442851f66742fd7c1e15b337e`
9. `b08c4dc2bcbc9ed92ef6fc4a49e418fb`
10. `a6df5c6ab575859c1ffebf934eb47ad8`

## Candidate — prompt label `candidate`, version 2

- `28041073697b681ca61de79bd5a25ab5`

## Official K4 `rag_slow` challenge — prompt label `production`, version 1

- `b4d029792a4e68cd0758851eab3a163b`
- `10154521f8b481c9010bc6087406428b`
- `157c9b49e5dfccdc5ce7144f4cc3748d`
- `b3ac63aec5fab0bb2659515cb996509a`
- `32899566dd7eb774e567a7a90f72cc73`

Mỗi trace có root `agent.run`, child span `rag.retrieve` và generation `llm.generate`.

## Run cuối cùng — regenerate log sạch, label `production`

Chạy lại sau khi xóa các record baseline chưa fix để `data/logs.jsonl` chỉ còn log đạt chuẩn (validator 100/100 trên 49 record). Đây là run khớp với log và dashboard nộp kèm.

Baseline (`qa`, `summary`):

1. `41396d93250b55f2b153c43dc99d8816`
2. `a3149dc8c8c94ad4602c199e2706da50`
3. `496b631778ca0d5a1e09657e272426c9`
4. `9195906e2f31f12ca491c224b6173d89`
5. `2c7bf734755fa091296af37bd5c032a6`
6. `cd07e4eff98a4f2b1f4ecca0da367091`
7. `f207198858f8db2085d303a09bcf5369`
8. `61983d2ed5c36fad497981d504f221f0`
9. `fcff5c5dcb3a03d045985255b150499f`
10. `63506c48765549873d19465c5bfc0e62`

Official K4 `rag_slow` challenge (feature `monitoring`):

- `30e399de002e4725b6d158b4dc2aaa09`
- `d6ef9add809db69569910b11055125ff`
- `c037e893082ce70f7041f40bd8e6afa7`
- `706320b60a12e1b86efa247209cee1ba`
- `6420376f132f9b69b7a87e59b867e756` — trace dùng cho waterfall trong report
