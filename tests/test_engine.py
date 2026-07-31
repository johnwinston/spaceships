from src import engine, rle, ruletable

LIFE = ruletable.totalistic_table("b3s23")


def cells_of(text):
    cells, _ = rle.parse(text)
    return set(cells)


def normalise(cells):
    min_x = min(c[0] for c in cells)
    min_y = min(c[1] for c in cells)
    return {(x - min_x, y - min_y) for x, y in cells}


def test_blinker_period_2():
    blinker = cells_of("x=3,y=1,rule=B3/S23\n3o!")
    g1 = engine.step(blinker, LIFE)
    g2 = engine.step(g1, LIFE)
    assert g1 != blinker
    assert g2 == blinker


def test_block_still_life():
    block = cells_of("x=2,y=2,rule=B3/S23\n2o$2o!")
    assert engine.step(block, LIFE) == block


def test_glider_translates_one_diagonal_per_period():
    glider = cells_of("x=3,y=3,rule=B3/S23\nbob$2bo$3o!")
    current = glider
    for _ in range(4):
        current = engine.step(current, LIFE)
    # after one full period the glider has moved (+1, +1)
    assert current == {(x + 1, y + 1) for x, y in glider}


def test_run_yields_initial_generation_first():
    glider = cells_of("x=3,y=3,rule=B3/S23\nbob$2bo$3o!")
    gens = list(engine.run(glider, LIFE, 4))
    assert len(gens) == 5
    assert gens[0] == glider
    assert normalise(gens[4]) == normalise(glider)
