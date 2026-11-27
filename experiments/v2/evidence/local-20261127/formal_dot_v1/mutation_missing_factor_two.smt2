; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () Int)
(declare-fun q () Int)
(declare-fun y () Int)
(declare-fun r () Int)
(assert
 (>= x 0))
(assert
 (>= q 0))
(assert
 (>= y 0))
(assert
 (>= r 0))
(assert
 (<= x 255))
(assert
 (<= q 255))
(assert
 (<= y 255))
(assert
 (<= r 255))
(assert
 (let ((?x32 (* y r)))
 (let ((?x31 (* x q)))
 (let ((?x33 (+ ?x31 ?x32)))
 (let ((?x29 (* r r)))
 (let ((?x30 (+ (+ (+ (* x x) (* y y)) (* q q)) ?x29)))
 (let ((?x19 (- x q)))
 (let ((?x20 (* ?x19 ?x19)))
 (let ((?x23 (+ ?x20 (* (- y r) (- y r)))))
 (and (distinct ?x23 (- ?x30 ?x33)) true))))))))))
(check-sat)
