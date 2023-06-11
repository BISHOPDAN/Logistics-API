from django.contrib import admin, messages

from .models import ProjectApiKey


class ProjectApiKeyAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "pub_key",
    )
    search_fields = ("user", "pub_key")

    def save_model(self, request, obj, form, change):
        created = not obj.pk

        if created:
            obj.save()

            # Get the sec key from the obj and pass to a variable then remove it
            key = obj.demo_sec
            obj.demo_sec = ''
            obj.save()

            message = (
                "The API Secret key for {} is: {} ".format(obj.user, key)
                + "Please store it somewhere safe: "
                + "you will not be able to see it again."
            )
            messages.add_message(request, messages.WARNING, message)

        else:
            obj.save()


admin.site.register(ProjectApiKey, ProjectApiKeyAdmin)
