class Node:

    def __init__(self, data, pnext=None):
        self.data = data
        self.pnext = pnext
        self.length = 1
        self.head = self

    def __repr__(self):
        return str(self.data)

    def is_empty(self):
        return self.length == 0

    def append(self, node):
        if not isinstance(node, Node):
            node = Node(node)
        if self.is_empty():
            self.head = node
            self.length += 1
        else:
            item = self.head
            while item.pnext:
                item = item.pnext
            item.pnext = node
            self.length += 1

    def find_reverse_kth_node(self, k):
        if k < 0:
            return None
        if not self.length:
            return None
        if self.length < k:
            return None
        f_item = self.head
        step = 0
        while step < k - 1:
            f_item = f_item.pnext
            step += 1
        s_item = self.head
        while f_item.pnext:
            s_item = s_item.pnext
            f_item = f_item.pnext
        return s_item

    def node_print(self):
        item = self.head
        while item:
            print(item)
            item = item.pnext


if __name__ == '__main__':
    # node = Node(11)
    # print(node)

    # for i in range(10):
    #     node.append(Node(i))
    # print(node.length)
    # node.node_print()

    # print(node.find_reverse_kth_node(0))

    import cProfile
    import re
    cProfile.run('re.compile("foolbar")')

