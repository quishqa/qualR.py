# qualR.py
This is [qualR](https://github.com/quishqa/qualR) package python flavored.
It will help you to bring [CETESB QUALAR](https://cetesb.sp.gov.br/ar/qualar/) data to your python session.

## Installation

You can install `qualRpy` by cloning this repository and install it via pip:

```
git clone https://github.com/quishqa/qualR.py.git
pip install .
```

Or you can install it directly from this repository by doing:

```
pip install git+https://github.com/quishqa/qualR.py.git
```

## Example of use

Downloading ozone information from Pinheiros air quality station,
from January first to january 7th, 2021.

```python
import qualRpy.qualR as qr

user_name = "your_awesome_mail@amail.com"
my_password = "a_mistery_password"

start_date = "01/01/2021"
end_date = "07/01/2021"

o3_code = 63 # you can check it by qr.cetesb_aqs()
pin_code = 99 # you can check it by qr.ceteb_param()

o3_pin = qr.cetesb_data_download(
  user_name,
  my_password,
  start_date,
  end_date,
  o3_code,
  pin_code
  )
```


## Acknowledgments
Very thankful to CETESB for make this data available and to the awesome LAPAT-IAG team.
