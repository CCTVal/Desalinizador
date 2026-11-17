"""Comprueba continuidad después de la bomba y flujo sostenido en la descarga."""
from pathlib import Path
from playwright.sync_api import sync_playwright

SHOTS = Path(__file__).resolve().parents[1] / 'documentacion' / 'capturas'

with sync_playwright() as p:
    browser = p.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1440, 'height':1100}, reduced_motion='reduce')
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8001')
    page.wait_for_selector('#viewport[data-ready="true"]')
    page.locator('#pump-toggle').click()
    page.locator('#valve-opening').evaluate('(node) => { node.value = Number(node.value) > 0 ? 0 : 100; node.dispatchEvent(new Event("input", {bubbles:true})); }')
    assert float(page.locator('#viewport').get_attribute('data-water-path-length')) > 5
    outlet = list(map(float, page.locator('#viewport').get_attribute('data-water-final-outlet').split(',')))
    assert outlet[2] > 1.2 and .34 < outlet[1] < .36
    assert page.locator('#viewport').get_attribute('data-water-discharge-reached') == 'true'
    assert 'descarga final' in page.locator('#water-status').inner_text()
    rect = page.locator('#viewport').bounding_box()
    x, y = rect['x'] + rect['width'] / 2, rect['y'] + rect['height'] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x - rect['height'] * .16, y, steps=6)
    page.mouse.up()
    page.screenshot(path=str(SHOTS / 'recorrido-descarga.png'), full_page=True)
    page.emulate_media(reduced_motion='no-preference')
    page.locator('#viewport').scroll_into_view_if_needed()
    first_distance = float(page.locator('#viewport').get_attribute('data-water-travelled-m'))
    first_frame = page.locator('#viewport canvas').screenshot()
    page.wait_for_timeout(350)
    assert float(page.locator('#viewport').get_attribute('data-water-travelled-m')) > first_distance
    assert first_frame != page.locator('#viewport canvas').screenshot(), 'La animación debe continuar después de alcanzar la descarga'
    assert page.locator('#viewport').get_attribute('data-water-open') == 'true'
    page.locator('#piece').select_option('171')
    page.locator('#piece-x').fill('.1')
    page.locator('#piece-x').press('Tab')
    assert page.locator('#viewport').get_attribute('data-connection-state') == 'disconnected'
    assert page.locator('#viewport').get_attribute('data-water-open') == 'false'
    page.locator('#reset-pieces').click()
    assert page.locator('#viewport').get_attribute('data-water-open') == 'true'
    page.locator('#valve-opening').evaluate('(node) => { node.value = Number(node.value) > 0 ? 0 : 100; node.dispatchEvent(new Event("input", {bubbles:true})); }')
    assert page.locator('#viewport').get_attribute('data-water-open') == 'false'
    assert not errors, errors
    browser.close()
print('OK: colector superior, bajante y descarga final; flujo continuo y corte al separar la bajante.')
