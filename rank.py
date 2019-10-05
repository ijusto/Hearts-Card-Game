class Rank:
    def __init__(self, num):
        self.num = num
        self.string = ''

        court_n_ace = ["J", "Q", "K", "A"]

        if num > 1 and num < 11:
            self.string = str(num)
        elif num < 15:
            self.string = court_n_ace[num - 11]
        else:
            print('Invalid rank number')