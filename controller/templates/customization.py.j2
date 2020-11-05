from restapi.customizer import BaseCustomizer

# from restapi.utilities.logs import log


class Customizer(BaseCustomizer):
    @staticmethod
    def custom_user_properties_pre(properties):
        """
            executed just before user creation
            use this method to removed or manipulate input properties
            before sending to the database
        """
        extra_properties = {}
        # if "myfield" in properties:
        #     extra_properties["myfield"] = properties["myfield"]
        return properties, extra_properties

    @staticmethod
    def custom_user_properties_post(user, properties, extra_properties, db):
        """
            executed just after user creation
            use this method to implement extra operation needed to create a user
            e.g. store additional relationships
        """
        pass

    @staticmethod
    def manipulate_profile(ref, user, data):
        """
            execute before sending data from the profile endpoint
            use this method to add additonal information to the user profile
        """
        # data["CustomField"] = user.custom_field

        return data

    @staticmethod
    def get_custom_input_fields(request, scope):

        # required = request and request.method == "POST"
        """
        if scope == BaseCustomizer.ADMIN:
            return {
                'custom_field': fields.Int(
                    required=required,
                    # validate=validate.Range(min=0, max=???),
                    validate=validate.Range(min=0),
                    label="CustomField",
                    description="This is a custom field"
                )
            }
        # these are editable fields in profile
        if scope == BaseCustomizer.PROFILE:
            return {}

        # these are additional fields in registration form
        if scope == BaseCustomizer.REGISTRATION:
            return {}
        """
        return {}

    @staticmethod
    def get_custom_output_fields(request):
        """
            this method is used to extend the output model of admin users
        """
        return Customizer.get_custom_input_fields(request, scope=BaseCustomizer.ADMIN)
