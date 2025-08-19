from django import forms
from django.utils.safestring import mark_safe
from django.forms.utils import flatatt  # ✅ Correct import

class ColorPaletteWidget(forms.TextInput):
    def render(self, name, value, attrs=None, renderer=None):
        # Prepare input field
        final_attrs = self.build_attrs(attrs, extra_attrs={'type': 'text', 'name': name})
        final_attrs['value'] = value or ''
        input_html = f'<input{flatatt(final_attrs)} />'

        # Define color palette
        colors = [
            "#1E3A8A", "#2563EB", "#3B82F6",  # Blues
            "#059669", "#10B981", "#22C55E",  # Greens
            "#DC2626", "#EF4444", "#F87171",  # Reds
            "#FACC15", "#FBBF24", "#F59E0B"   # Yellows
        ]

        # Generate clickable color blocks
        # blocks_html = '<div style="margin-top:5px;">'
        # for c in colors:
        #     blocks_html += (
        #         f'<div onclick="selectColor_{name}(\'{c}\')" '
        #         f'style="display:inline-block;width:30px;height:30px;'
        #         f'margin:2px;cursor:pointer;background-color:{c};border:1px solid #000;"></div>'
        #     )
        # blocks_html += '</div>'

        blocks_html = '<div style="margin-top:8px; margin-left:8px">'
        for c in colors:
            blocks_html += (
                f'<div onclick="selectColor_{name}(\'{c}\')" '
                f'style="display:inline-block;width:30px;height:30px;'
                f'margin:3px;cursor:pointer;background-color:{c};border:1px solid #000;"></div>'
            )
        blocks_html += '</div>'

        # Inline JavaScript to update input value
        script_html = f"""
        <script>
            function selectColor_{name}(color) {{
                var input = document.getElementsByName("{name}")[0];
                input.value = color;
            }}
        </script>
        """

        return mark_safe(input_html + blocks_html + script_html)



class ToggleSwitchWidget(forms.CheckboxInput):
    def render(self, name, value, attrs=None, renderer=None):
        checked = 'checked' if value else ''
        html = f"""
        <label class="custom-toggle-switch">
            <input type="checkbox" name="{name}" {checked}>
            <span class="custom-slider"></span>
        </label>

        <style>
            .custom-toggle-switch {{
                position: relative !important;
                width: 50px !important;
                height: 24px !important;
                display: inline-block !important;
                vertical-align: middle !important;
            }}
            .custom-toggle-switch input {{
                display: none !important;
            }}
            .custom-slider {{
                position: absolute !important;
                cursor: pointer !important;
                top: 0 !important;
                left: 0 !important;
                right: 0 !important;
                bottom: 0 !important;
                background-color: #ccc !important;
                transition: 0.3s !important;
                border-radius: 50px !important;
            }}
            .custom-slider:before {{
                position: absolute !important;
                content: "" !important;
                height: 18px !important;
                width: 18px !important;
                left: 3px !important;
                bottom: 3px !important;
                background-color: white !important;
                transition: 0.3s !important;
                border-radius: 50% !important;
            }}
            input:checked + .custom-slider {{
                background-color: #4CAF50 !important;
            }}
            input:checked + .custom-slider:before {{
                transform: translateX(26px) !important;
            }}
        </style>
        """
        return mark_safe(html)