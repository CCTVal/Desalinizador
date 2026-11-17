"""Aspersor conectado: pulverización, corte y movimiento reducido."""
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1440, 'height':1100}, reduced_motion='reduce')
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8001')
    page.wait_for_selector('#viewport[data-ready="true"]')
    view = page.locator('#viewport')
    assert view.get_attribute('data-spray-active') == 'false'
    page.locator('#pump-toggle').click()
    page.locator('#valve-opening').evaluate('(node) => { node.value = Number(node.value) > 0 ? 0 : 100; node.dispatchEvent(new Event("input", {bubbles:true})); }')
    assert view.get_attribute('data-spray-active') == 'true'
    assert int(view.get_attribute('data-spray-drop-count')) > 24
    origin = list(map(float, view.get_attribute('data-spray-origin').split(',')))
    assert 1.96 < origin[1] < 1.98
    assert 1.26 < float(view.get_attribute('data-spray-stop-y')) < 1.28
    page.emulate_media(reduced_motion='no-preference')
    first = page.locator('#viewport canvas').screenshot()
    page.wait_for_timeout(250)
    assert first != page.locator('#viewport canvas').screenshot()
    rect = view.bounding_box()
    x, y = rect['x'] + rect['width'] / 2, rect['y'] + rect['height'] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x - rect['height'] * .16, y, steps=6)
    page.mouse.up()
    page.screenshot(path=str(Path('documentacion/capturas/aspersor.png')), full_page=True)
    page.locator('#valve-opening').evaluate('(node) => { node.value = Number(node.value) > 0 ? 0 : 100; node.dispatchEvent(new Event("input", {bubbles:true})); }')
    assert view.get_attribute('data-spray-active') == 'false'
    page.locator('#valve-opening').evaluate('(node) => { node.value = Number(node.value) > 0 ? 0 : 100; node.dispatchEvent(new Event("input", {bubbles:true})); }')
    assert view.get_attribute('data-spray-active') == 'false', 'Debe esperar a que llegue el agua'
    page.emulate_media(reduced_motion='reduce')
    page.wait_for_selector('#viewport[data-spray-active="true"]')
    assert view.get_attribute('data-spray-active') == 'true'
    page.locator('#piece').select_option('158')
    page.locator('#piece-x').fill('.1')
    page.locator('#piece-x').press('Tab')
    assert view.get_attribute('data-connection-state') == 'disconnected'
    assert view.get_attribute('data-spray-active') == 'false'
    page.locator('#reset-pieces').click()
    assert view.get_attribute('data-spray-active') == 'true'
    page.locator('#pump-toggle').click()
    assert view.get_attribute('data-spray-active') == 'false'
    assert not errors, errors
    browser.close()
print('OK: sprinkler arrival, droplets, reduced motion, valve/pump stop and disconnection.')
