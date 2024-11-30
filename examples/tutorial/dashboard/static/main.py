from cannula.codegen import render_code
from cannula.scalars import date, util

from pyscript import document


def run_codegen(event):
    input_text = document.querySelector("#input")
    schema = input_text.value
    output_div = document.querySelector("#output")
    output_div.innerText = render_code(
        [schema],
        scalars=[
            date.Datetime,
            date.Date,
            date.Time,
            util.JSON,
            util.UUID,
        ],
    )


generate_button = document.querySelector("#generate-btn")
generate_button.enabled = True
