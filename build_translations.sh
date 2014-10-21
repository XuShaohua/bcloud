#!/bin/bash

pushd po > /dev/null
xgettext --language=Python --keyword=_ --output=bcloud.pot --from-code=UTF-8 `find ../bcloud -name "*.py" | sort`
popd > /dev/null
