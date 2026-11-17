"""Giro de la vista sin mover conexiones; parada y arrastre manual."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1440, 'height':1100}, reduced_motion='reduce')
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8001')
    page.wait_for_selector('#viewport[data-ready="true"]')
    view, button = page.locator('#viewport'), page.locator('#rotate-view')
    assert button.get_attribute('aria-pressed') == 'false'
    before = view.locator('canvas').screenshot()
    button.click()
    page.wait_for_timeout(400)
    assert button.inner_text() == 'Detener giro'
    assert before != view.locator('canvas').screenshot()
    assert view.get_attribute('data-connection-state') == 'connected'
    assert view.get_attribute('data-pump-state') == 'off'
    button.click()
    stopped = view.locator('canvas').screenshot()
    page.wait_for_timeout(200)
    assert stopped == view.locator('canvas').screenshot()
    button.click()
    rect = view.bounding_box()
    page.mouse.move(rect['x'] + rect['width'] * .3, rect['y'] + rect['height'] * .5)
    page.mouse.down()
    page.mouse.move(rect['x'] + rect['width'] * .4, rect['y'] + rect['height'] * .5, steps=4)
    page.mouse.up()
    assert button.get_attribute('aria-pressed') == 'false'
    button.click()
    page.locator('#frame-view').click()
    assert button.get_attribute('aria-pressed') == 'false'
    page.set_viewport_size({'width':390, 'height':844})
    button.click()
    assert button.get_attribute('aria-pressed') == 'true'
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    button.click()
    assert not errors, errors
    browser.close()
print('OK: automatic rotation, stop, manual drag, reset and mobile; circuit unchanged.')
