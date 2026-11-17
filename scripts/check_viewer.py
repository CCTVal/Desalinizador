"""Comprueba el visor mínimo: zoom y abrir/cerrar agua."""
from pathlib import Path
from playwright.sync_api import sync_playwright

SHOTS = Path(__file__).resolve().parents[1] / 'documentacion' / 'capturas'
SHOTS.mkdir(parents=True, exist_ok=True)


def slider(page, value):
    page.locator('#zoom').evaluate('(node, value) => { node.value = value; node.dispatchEvent(new Event("input", {bubbles: true})); }', str(value))


with sync_playwright() as p:
    browser = p.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8001')
    page.wait_for_selector('#viewport[data-ready="true"]')
    page.locator('#pump-toggle').click()
    assert page.locator('#viewport').get_attribute('data-parts') == '210'
    assert page.locator('#piece option').count() == 211
    assert page.locator('#viewer-title').inner_text() == 'P23.00-00-A008v2'
    slider(page, 200)
    assert page.locator('#zoom-value').inner_text() == '200 %'
    page.locator('#viewport').focus()
    page.keyboard.press('+')
    assert float(page.locator('#viewport').get_attribute('data-zoom')) > 2
    page.locator('#viewport').hover()
    previous = float(page.locator('#viewport').get_attribute('data-zoom'))
    page.mouse.wheel(0, 120)
    page.wait_for_timeout(100)
    assert float(page.locator('#viewport').get_attribute('data-zoom')) < previous
    slider(page, 100)
    before = page.locator('#viewport canvas').screenshot()
    rect = page.locator('#viewport').bounding_box()
    page.mouse.move(rect['x'] + rect['width'] / 2, rect['y'] + rect['height'] / 2)
    page.mouse.down()
    page.mouse.move(rect['x'] + rect['width'] / 2 + 70, rect['y'] + rect['height'] / 2 + 30, steps=5)
    page.mouse.up()
    rotated = page.locator('#viewport canvas').screenshot()
    assert before != rotated, 'Arrastrar debe girar la vista de la planta'
    page.mouse.down(button='right')
    page.mouse.move(rect['x'] + rect['width'] / 2 + 130, rect['y'] + rect['height'] / 2 + 50, steps=5)
    page.mouse.up(button='right')
    panned = page.locator('#viewport canvas').screenshot()
    assert panned != rotated, 'El botón derecho debe desplazar la vista'
    page.mouse.down(button='right')
    page.mouse.move(rect['x'] + rect['width'] / 2 + 170, rect['y'] + rect['height'] / 2 + 70, steps=5)
    page.mouse.up(button='right')
    assert panned != page.locator('#viewport canvas').screenshot(), 'El desplazamiento no debe deshacerse al mover el puntero'
    page.locator('#frame-view').click()
    assert before == page.locator('#viewport canvas').screenshot(), 'Encuadrar debe recuperar la vista inicial'
    page.locator('#valve-opening').evaluate('(node) => { node.value = Number(node.value) > 0 ? 0 : 100; node.dispatchEvent(new Event("input", {bubbles:true})); }')
    assert page.locator('#viewport').get_attribute('data-water-open') == 'true'
    assert before != page.locator('#viewport canvas').screenshot(), 'El agua debe ser visible'
    page.screenshot(path=str(SHOTS / 'planta-desktop.png'), full_page=True)
    page.emulate_media(reduced_motion='no-preference')
    frame = page.locator('#viewport canvas').screenshot()
    page.wait_for_timeout(150)
    assert frame != page.locator('#viewport canvas').screenshot(), 'El agua debe animarse'
    page.emulate_media(reduced_motion='reduce')
    slider(page, 400)
    closeup = page.locator('#viewport canvas').screenshot()
    page.locator('#valve-opening').evaluate('(node) => { node.value = Number(node.value) > 0 ? 0 : 100; node.dispatchEvent(new Event("input", {bubbles:true})); }')
    assert closeup != page.locator('#viewport canvas').screenshot(), 'La salida debe seguir visible con zoom máximo'
    page.locator('#valve-opening').evaluate('(node) => { node.value = Number(node.value) > 0 ? 0 : 100; node.dispatchEvent(new Event("input", {bubbles:true})); }')
    slider(page, 100)
    page.locator('#valve-opening').evaluate('(node) => { node.value = Number(node.value) > 0 ? 0 : 100; node.dispatchEvent(new Event("input", {bubbles:true})); }')
    assert page.locator('#viewport').get_attribute('data-water-open') == 'false'
    page.emulate_media(reduced_motion='reduce')
    assert before == page.locator('#viewport canvas').screenshot(), 'Cerrar agua restaura la escena'
    page.set_viewport_size({'width': 390, 'height': 844})
    page.locator('#valve-opening').evaluate('(node) => { node.value = Number(node.value) > 0 ? 0 : 100; node.dispatchEvent(new Event("input", {bubbles:true})); }')
    page.screenshot(path=str(SHOTS / 'planta-mobile.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    browser.close()
print('OK: giro, desplazamiento, encuadre, zoom, agua, movimiento reducido y móvil.')
