# Extension Example

This shows an example of using multiple schemas that extend functionality. The most simple case is to extend the `Query` or `Mutation` types. But any type can be extended.

The directory `schema` contains multiple graphql files that will be loaded if we specify a `pathlib.Path` type as the `schema` argument.

```python

import cannula
import pathlib

api = cannula.API(schema=pathlib.Path('./schema'))
```