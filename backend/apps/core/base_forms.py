from django import forms


class StyledFormMixin:
    """Auto-applies LIFEOS design-system CSS classes to every field widget so
    individual forms never have to repeat ``attrs={"class": "input"}``."""

    WIDGET_CLASSES = {
        forms.Select: "select",
        forms.SelectMultiple: "select",
        forms.Textarea: "textarea",
        forms.CheckboxInput: "checkbox-input",
        forms.RadioSelect: "radio-input",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css_class = "input"
            for widget_type, cls in self.WIDGET_CLASSES.items():
                if isinstance(widget, widget_type):
                    css_class = cls
                    break
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {css_class}".strip()


class StyledForm(StyledFormMixin, forms.Form):
    class Meta:
        abstract = True


class StyledModelForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        abstract = True
