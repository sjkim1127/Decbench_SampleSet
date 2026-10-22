namespace bounded {
struct Pair { int left; int right; };

__declspec(noinline) int read_pair(const Pair* object) {
    return object->left + object->right;
}

__declspec(noinline) int update_ref(int& value, int delta) {
    value += delta;
    return value;
}

__declspec(noinline) const int& choose_ref(const Pair& object, bool right) {
    if (right) return object.right;
    return object.left;
}
}

extern "C" int entry() {
    bounded::Pair object{7, 11};
    int value = 3;
    return bounded::read_pair(&object) + bounded::update_ref(value, 5)
        + bounded::choose_ref(object, true);
}
