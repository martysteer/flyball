# conductor/ — runs on Slate (Inky Pi)

The state authority. Owns channel/option state, the sentence stack, the render queue,
and the evolution loop; calls the image-gen backend; drives the Inky e-paper.
Interprets button *semantics* (Spark reports raw presses). See `../docs/03` and `../docs/04`.

_Empty scaffold — Claude Code fills this in starting at Milestone M0/M1._
