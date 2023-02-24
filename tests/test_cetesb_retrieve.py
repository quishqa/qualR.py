import unittest
import qualR.qualRpy.qualR as qr
import os
import pickle
import pandas as pd
user_name = os.environ.get('CETESB_USER')
my_password = os.environ.get('CETESB_PW')


class TestCetesbRetrieve(unittest.TestCase):

    def test_o3_pin(self):

        start_date = "01/01/2021"
        end_date = "07/01/2021"

        start_date = "01/01/2021"
        end_date = "07/01/2021"

        o3_code = 63 # you can check it by qr.cetesb_param()
        pin_code = 99 # you can check it by qr.ceteb_aqs()

        o3_pin = qr.cetesb_retrieve(
            user_name,
            my_password,
            start_date,
            end_date,
            o3_code,
            pin_code
)

        reference = pd.read_parquet('test_data/o3_pin.parquet')

        self.assertEqual(o3_pin.equal(reference), True, 'o3 test (pin) dataframe is different than the reference.')

    def test_o3_over_all_stations(self):

        start_date = "01/01/2021"
        end_date = "07/01/2021"

        o3_code = 63 # you can check it by qr.cetesb_param()
        aqs = qr.cetesb_aqs() # Loading all the aqs

        o3_aqs = {aqs_name: qr.cetesb_retrieve(user_name, my_password,
                                               start_date, end_date,
                                               o3_code, aqs_code)
                  for aqs_name, aqs_code in zip(aqs.name, aqs.code)}

        reference = pickle.load(open("test_data/o3_aqs.pkl", "rb"))



        self.assertEqual(o3_aqs.equal(reference), True, 'o3 test (all) dataframe is different than the reference.')


if __name__ == '__main__':
    unittest.main()
