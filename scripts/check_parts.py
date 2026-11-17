"""Verifica selección, inspección y traslado de sólidos CAD."""
from pathlib import Path
from playwright.sync_api import sync_playwright

SHOTS = Path(__file__).resolve().parents[1] / 'documentacion' / 'capturas'


with sync_playwright() as p:
    browser = p.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1100}, reduced_motion='reduce')
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8001')
    page.wait_for_selector('#viewport[data-ready="true"]')
    page.locator('#pump-toggle').click()
    assert page.locator('#piece option').count() == 211
    assert float(page.locator('#viewport').get_attribute('data-connection-gap-mm')) < .001
    assert abs(float(page.locator('#viewport').get_attribute('data-support-ground-clearance'))) < 1e-6
    page.locator('#piece').select_option('82')
    assert page.locator('#viewport').get_attribute('data-selected-part') == '83'
    assert page.locator('#piece-x').is_enabled()
    page.screenshot(path=str(SHOTS / 'pieza-seleccionada.png'), full_page=True)
    rect = page.locator('#viewport').bounding_box()
    x, y = rect['x'] + rect['width'] / 2, rect['y'] + rect['height'] * .405
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x, y - 35, steps=5)
    page.mouse.up()
    assert abs(float(page.locator('#piece-y').input_value())) > .01, 'La flecha verde debe trasladar la pieza'
    page.locator('#reset-piece').click()
    for axis, value in [('x', '.2'), ('y', '.1'), ('z', '-.15')]:
        page.locator('#piece-' + axis).fill(value)
        page.locator('#piece-' + axis).press('Tab')
    assert page.locator('#viewport').get_attribute('data-piece-offset') == '0.200,0.100,-0.150'
    page.locator('#reset-piece').click()
    assert page.locator('#viewport').get_attribute('data-piece-offset') == '0.000,0.000,0.000'
    # A sub-millimetre part must also be selectable and individually framed.
    page.locator('#piece').select_option('66')
    assert page.locator('#viewport').get_attribute('data-selected-part') == '67'
    page.locator('#isolate-piece').uncheck()
    page.locator('#piece').select_option('209')
    page.locator('#valve-opening').evaluate('(node) => { node.value = Number(node.value) > 0 ? 0 : 100; node.dispatchEvent(new Event("input", {bubbles:true})); }')
    original = list(map(float, page.locator('#viewport').get_attribute('data-water-outlet').split(',')))
    assert page.locator('#viewport').get_attribute('data-connection-state') == 'connected'
    page.locator('#piece-y').fill('.2')
    page.locator('#piece-y').press('Tab')
    updated = list(map(float, page.locator('#viewport').get_attribute('data-water-outlet').split(',')))
    assert abs(updated[1] - original[1] - .2) < .002, 'El chorro debe seguir al tubo'
    assert page.locator('#viewport').get_attribute('data-connection-state') == 'disconnected'
    assert page.locator('#viewport').get_attribute('data-water-open') == 'false', 'No puede fluir agua entre piezas separadas'
    assert float(page.locator('#viewport').get_attribute('data-connection-gap-mm')) > 199
    assert float(page.locator('#viewport').get_attribute('data-water-path-length')) > .3
    inlet = list(map(float, page.locator('#viewport').get_attribute('data-water-destination').split(',')))
    page.locator('#piece').select_option('123')
    page.locator('#piece-z').fill('.1')
    page.locator('#piece-z').press('Tab')
    moved_inlet = list(map(float, page.locator('#viewport').get_attribute('data-water-destination').split(',')))
    assert abs(moved_inlet[2] - inlet[2] - .1) < .002, 'La manguera debe seguir también al tubo receptor'
    valve = list(map(float, page.locator('#viewport').get_attribute('data-water-valve').split(',')))
    page.locator('#piece').select_option('207')
    page.locator('#piece-x').fill('-.1')
    page.locator('#piece-x').press('Tab')
    moved_valve = list(map(float, page.locator('#viewport').get_attribute('data-water-valve').split(',')))
    assert abs(moved_valve[0] - valve[0] + .1) < .002, 'La traza debe seguir la llave verde'
    page.locator('#reset-pieces').click()
    assert page.locator('#piece').input_value() == ''
    restored = list(map(float, page.locator('#viewport').get_attribute('data-water-outlet').split(',')))
    assert restored == original
    assert page.locator('#viewport').get_attribute('data-connection-state') == 'connected'
    assert page.locator('#viewport').get_attribute('data-water-open') == 'true'
    assert list(map(float, page.locator('#viewport').get_attribute('data-water-destination').split(','))) == inlet
    assert page.locator('#piece-x').is_disabled()
    # Representative structure, fastener, vessel, pipe, valve and terminal solids.
    for index in [0, 66, 82, 123, 207, 209]:
        page.locator('#piece').select_option(str(index))
        assert page.locator('#viewport').get_attribute('data-selected-part') == str(index + 1)
    page.locator('#reset-pieces').click()
    page.locator('#valve-opening').evaluate('(node) => { node.value = Number(node.value) > 0 ? 0 : 100; node.dispatchEvent(new Event("input", {bubbles:true})); }')
    page.emulate_media(reduced_motion='no-preference')
    page.locator('#valve-opening').evaluate('(node) => { node.value = Number(node.value) > 0 ? 0 : 100; node.dispatchEvent(new Event("input", {bubbles:true})); }')
    first_progress = float(page.locator('#viewport').get_attribute('data-water-progress'))
    page.wait_for_timeout(250)
    next_progress = float(page.locator('#viewport').get_attribute('data-water-progress'))
    assert 0 <= first_progress < next_progress < 1, 'El agua debe recorrer el circuito progresivamente'
    page.emulate_media(reduced_motion='reduce')
    page.set_viewport_size({'width': 390, 'height': 844})
    page.locator('#piece').select_option('207')
    page.screenshot(path=str(SHOTS / 'pieza-mobile.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    browser.close()
print('OK: 210 piezas seleccionables, aislamiento, X/Y/Z, restauración, agua unida al tubo y móvil.')
