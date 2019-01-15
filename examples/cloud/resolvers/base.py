
import cannula


class OpenStackBase(cannula.datasource.http.HTTPDataSource):

    # The name of the service in the catalog for the logged in user.
    catalog_name = None

    def get_service_url(self, region: str, path: str):
        """Find the correct service url for region.

        The Openstack services usually add the project id in the url of
        the service. So for each user you need to get the url from the
        service catalog.
        """
        if not hasattr(self.context, 'user'):
            raise Exception('Missing auth_user did you login?')

        if self.catalog_name is None:
            raise AttributeError('catalog_name not set')

        # normalize the path
        if path.startswith('/'):
            path = path[1:]

        service = self.context.user.get_service_url(self.catalog_name, region)

        if service is None:
            raise AttributeError(f'No service url found for {region}')

        if service.endswith('/'):
            return f'{service}{path}'
        return f'{service}/{path}'

    def will_send_request(self, request):
        if hasattr(self.context, 'user'):
            request.headers.update({'X-Auth-Token': self.context.user.auth_token})
        return request
