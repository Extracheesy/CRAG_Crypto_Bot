from exchanger import MyExchanger
import config

def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.

# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    Crag = MyExchanger('ftx', 10000, config.FILTER_STRONG_BUY, config.INTERVAL)
    while True:
        Crag.next_step()

    print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
