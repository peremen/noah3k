#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
from web.contrib.template import render_mako

desktop_render = render_mako(
    directories = [os.path.join(os.path.dirname(__file__), 'templates/desktop/').replace('\\','/'),],
    input_encoding = 'utf-8', output_encoding = 'utf-8',
)

classic_render = render_mako(
    directories = [os.path.join(os.path.dirname(__file__), 'templates/classic/').replace('\\','/'),],
    input_encoding = 'utf-8', output_encoding = 'utf-8',
)

mobile_render = render_mako(
    directories = [os.path.join(os.path.dirname(__file__), 'templates/mobile/').replace('\\','/'),],
    input_encoding = 'utf-8', output_encoding = 'utf-8',
)
render = {
        'default': desktop_render, 
        'classic': classic_render, 
        'm': mobile_render,
}
