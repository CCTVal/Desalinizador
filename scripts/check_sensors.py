"""Prueba de lecturas simuladas, fichas en el CAD y escenarios del usuario."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1100}, reduced_motion='reduce')
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('http://127.0.0.1:8001')
    page.wait_for_selector('#viewport[data-ready="true"]')
    def input_value(selector, value, event='input'):
        page.locator(selector).evaluate('(node, args) => { node.value = args[0]; node.dispatchEvent(new Event(args[1], {bubbles:true})); }', [value, event])
    def readings():
        return page.locator('#viewport').evaluate('(node) => node.simulatedReadings')
    assert readings()['102']['value'] is None
    page.locator('#pump-toggle').click()
    input_value('#valve-opening', 100)
    values = readings()
    assert values['102']['value'] > values['105']['value']
    assert values['119']['value'] == 20
    page.locator('[data-sensor-piece="103"]').click()
    assert page.locator('#sensor-info').is_visible()
    assert 'Simulado:' in page.locator('#sensor-live-reading').inner_text()
    initial = page.locator('#sensor-live-reading').inner_text()
    input_value('#pump-frequency', 35)
    assert page.locator('#sensor-live-reading').inner_text() != initial
    assert readings()['119']['value'] == 20
    input_value('#water-heat', 500, 'change')
    hot = readings()['119']['value']
    assert hot > 20
    page.locator('[data-sensor-piece="120"]').click()
    assert 'PT100 ideal:' in page.locator('#sensor-live-status').inner_text()
    input_value('#pump-frequency', 50)
    assert 20 < readings()['119']['value'] < hot
    input_value('#pump-frequency', 15)
    assert readings()['135']['state'] == 'below'
    assert 'Por debajo' in page.locator('#sensor-range-135').inner_text()
    input_value('#water-temperature', '', 'change')
    assert readings()['119']['value'] is None
    assert readings()['102']['value'] is not None
    input_value('#water-temperature', 20, 'change')
    input_value('#water-heat', 0, 'change')
    input_value('#pump-frequency', 50)
    page.locator('#piece').select_option('73')
    viewport = page.locator('#viewport')
    assert float(viewport.get_attribute('data-gauge74-pressure-bar')) > float(viewport.get_attribute('data-gauge72-pressure-bar'))
    page.locator('#piece').select_option('102')
    page.locator('#piece-x').fill('.1'); page.locator('#piece-x').press('Tab')
    assert all(r['value'] is None for r in readings().values())
    page.locator('#reset-piece').click()
    assert readings()['102']['value'] is not None
    input_value('#valve-opening', 0)
    assert readings()['102']['value'] is None and readings()['135']['value'] == 0
    input_value('#valve-opening', 100)
    page.locator('#piece').select_option('')
    page.screenshot(path='documentacion/capturas/sensores-simulados-desktop.png', full_page=True)
    page.set_viewport_size({'width':390, 'height':844})
    page.locator('[data-sensor-piece="136"]').click()
    assert page.locator('#sensor-info').is_visible()
    assert 'L/min' in page.locator('#sensor-live-reading').inner_text()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path='documentacion/capturas/sensores-simulados-mobile.png', full_page=True)
    assert not errors, errors
    browser.close()
print('OK: lecturas, fichas vivas, energía térmica, rango, desconexión, cierre y móvil.')
